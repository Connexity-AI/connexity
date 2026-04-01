"""LiteLLM-backed chat completions with retries and configurable providers.

Model resolution (used after merging per-call config with
``Settings.LLM_DEFAULT_MODEL`` / ``Settings.LLM_DEFAULT_PROVIDER``):

1. If ``model`` contains ``/``, it is treated as a full LiteLLM routing id
   (e.g. ``anthropic/claude-3-5-sonnet-20241022``) and used as-is.
2. Else if ``provider`` is set, returns ``"{normalized_provider}/{model}"``
   (aliases: ``openai``, ``anthropic``).
3. Else returns ``model`` alone so LiteLLM can apply its default routing
   (e.g. bare ``gpt-4o``).

If the effective ``model`` is missing after merging defaults, raises
``ValueError``.
"""

import logging
import time
from typing import Any, Literal, Protocol

import litellm
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    BadGatewayError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from pydantic import BaseModel, Field
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

LLMExtraValue = str | int | float | bool | None

LLMRole = Literal["system", "user", "assistant", "tool"]


class LLMSettingsView(Protocol):
    """Subset of :class:`~app.core.config.Settings` read by the LLM service."""

    LLM_DEFAULT_MODEL: str | None
    LLM_DEFAULT_PROVIDER: str | None
    LLM_RETRY_MAX_ATTEMPTS: int
    LLM_RETRY_MIN_WAIT_SECONDS: float
    LLM_RETRY_MAX_WAIT_SECONDS: float


class LLMMessage(BaseModel):
    role: LLMRole
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class LLMCallConfig(BaseModel):
    """Per-call overrides; ``None`` means fall back to :class:`Settings`."""

    model: str | None = None
    provider: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_seconds: float | None = None
    response_format: dict[str, object] | None = Field(
        default=None,
        description="Provider-native structured output (e.g. OpenAI json_schema)",
    )
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        description="OpenAI-format tool/function definitions for function calling",
    )
    extra: dict[str, LLMExtraValue] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: dict[str, int] = Field(default_factory=dict)
    latency_ms: int | None = None
    response_cost_usd: float | None = Field(
        default=None,
        description="LiteLLM-computed USD cost from _hidden_params.response_cost",
    )
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        description="Tool calls from the assistant message (OpenAI-compatible dicts)",
    )


_PROVIDER_ALIASES: dict[str, str] = {
    "anthropic": "anthropic",
    "openai": "openai",
}


def resolve_litellm_model(model: str, provider: str | None) -> str:
    """Build the LiteLLM ``model`` string from a bare id and optional provider."""
    stripped = model.strip()
    if not stripped:
        msg = "LLM model must be a non-empty string"
        raise ValueError(msg)
    if "/" in stripped:
        return stripped
    if provider is not None and provider.strip():
        key = provider.strip().lower()
        normalized = _PROVIDER_ALIASES.get(key, key)
        return f"{normalized}/{stripped}"
    return stripped


def _merge_effective_model_provider(
    config: LLMCallConfig | None,
    app_settings: LLMSettingsView,
) -> tuple[str, str | None]:
    c = config or LLMCallConfig()
    model = c.model if c.model is not None else app_settings.LLM_DEFAULT_MODEL
    provider = (
        c.provider if c.provider is not None else app_settings.LLM_DEFAULT_PROVIDER
    )
    if model is None:
        msg = (
            "No LLM model configured: set LLMCallConfig.model or "
            "LLM_DEFAULT_MODEL in the environment"
        )
        raise ValueError(msg)
    resolved = resolve_litellm_model(model, provider)
    return resolved, provider


def _log_retry(retry_state: RetryCallState) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    attempt = retry_state.attempt_number
    wait = retry_state.next_action.sleep if retry_state.next_action else 0
    logger.warning(
        "LLM call failed (attempt %d), retrying in %.1fs: %s: %s",
        attempt,
        wait,
        type(exc).__name__ if exc else "unknown",
        exc,
    )


def _is_transient_llm_error(exc: BaseException) -> bool:
    if isinstance(
        exc,
        RateLimitError
        | Timeout
        | APIConnectionError
        | ServiceUnavailableError
        | BadGatewayError
        | InternalServerError,
    ):
        return True
    if isinstance(exc, APIError):
        code = getattr(exc, "status_code", None)
        if code is not None and int(code) >= 500:
            return True
    return False


def _usage_to_dict(usage_obj: object) -> dict[str, int]:
    """Map provider usage to int counts, including common cache fields."""
    out: dict[str, int] = {}
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        raw = getattr(usage_obj, key, None)
        if raw is not None:
            out[key] = int(raw)

    details = getattr(usage_obj, "prompt_tokens_details", None)
    if details is not None:
        cached = getattr(details, "cached_tokens", None)
        if cached is None and isinstance(details, dict):
            cached = details.get("cached_tokens")
        if cached is not None:
            out["cached_prompt_tokens"] = int(cached)

    return out


def _response_cost_usd_from_litellm(response: object) -> float | None:
    hidden = getattr(response, "_hidden_params", None)
    if not isinstance(hidden, dict):
        return None
    raw = hidden.get("response_cost")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _normalize_tool_calls(raw: object) -> list[dict[str, Any]] | None:
    """Convert provider tool_calls to JSON-serializable dicts."""
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        return None
    out: list[dict[str, Any]] = []
    for tc in raw:
        if isinstance(tc, dict):
            out.append(tc)
            continue
        dumped = getattr(tc, "model_dump", None)
        if callable(dumped):
            out.append(dumped(mode="json"))
            continue
        fn = getattr(tc, "function", None)
        fn_name = getattr(fn, "name", None) if fn is not None else None
        fn_args = getattr(fn, "arguments", None) if fn is not None else None
        if fn_name is not None:
            out.append(
                {
                    "id": getattr(tc, "id", "") or "",
                    "type": getattr(tc, "type", None) or "function",
                    "function": {"name": fn_name, "arguments": fn_args or "{}"},
                }
            )
        else:
            out.append({"raw": repr(tc)})
    return out or None


def _content_from_response(response: object) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        return ""
    first = choices[0]
    message = getattr(first, "message", None)
    if message is None:
        return ""
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    return ""


def _tool_calls_from_response(response: object) -> list[dict[str, Any]] | None:
    choices = getattr(response, "choices", None)
    if not choices:
        return None
    first = choices[0]
    message = getattr(first, "message", None)
    if message is None:
        return None
    raw = getattr(message, "tool_calls", None)
    return _normalize_tool_calls(raw)


def _llm_message_to_litellm_dict(m: LLMMessage) -> dict[str, Any]:
    """Serialize :class:`LLMMessage` for ``litellm.acompletion``."""
    d: dict[str, Any] = {"role": m.role}
    if m.tool_calls is not None:
        d["tool_calls"] = m.tool_calls
    if m.tool_call_id is not None:
        d["tool_call_id"] = m.tool_call_id
    if m.name is not None:
        d["name"] = m.name
    if m.content is not None:
        d["content"] = m.content
    elif m.role == "assistant" and m.tool_calls:
        d["content"] = None
    else:
        d["content"] = ""
    return d


async def _acompletion_once(
    *,
    model: str,
    message_dicts: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    temperature: float | None,
    max_tokens: int | None,
    timeout: float | None,
    response_format: dict[str, object] | None,
    extra: dict[str, LLMExtraValue],
) -> object:
    kwargs: dict[str, object] = {
        "model": model,
        "messages": message_dicts,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if timeout is not None:
        kwargs["timeout"] = timeout
    if response_format is not None:
        kwargs["response_format"] = response_format
    if tools is not None:
        kwargs["tools"] = tools
    for k, v in extra.items():
        if v is not None:
            kwargs[k] = v
    return await litellm.acompletion(**kwargs)


async def call_llm(
    messages: list[LLMMessage],
    config: LLMCallConfig | None = None,
    *,
    app_settings: LLMSettingsView | None = None,
) -> LLMResponse:
    """Run a chat completion with exponential backoff on transient failures."""
    app_settings = app_settings or settings
    resolved_model, _ = _merge_effective_model_provider(config, app_settings)
    c = config or LLMCallConfig()

    temperature = c.temperature
    max_tokens = c.max_tokens
    timeout = c.timeout_seconds
    response_format = c.response_format
    extra = dict(c.extra)
    tools = c.tools

    message_dicts = [_llm_message_to_litellm_dict(m) for m in messages]

    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(app_settings.LLM_RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(
            multiplier=1,
            min=app_settings.LLM_RETRY_MIN_WAIT_SECONDS,
            max=app_settings.LLM_RETRY_MAX_WAIT_SECONDS,
        ),
        retry=retry_if_exception(_is_transient_llm_error),
        before_sleep=_log_retry,
        reraise=True,
    ):
        with attempt:
            started = time.perf_counter()
            response = await _acompletion_once(
                model=resolved_model,
                message_dicts=message_dicts,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                response_format=response_format,
                extra=extra,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage_obj = getattr(response, "usage", None)
            usage = _usage_to_dict(usage_obj) if usage_obj is not None else {}
            response_model = getattr(response, "model", None) or resolved_model
            tool_calls = _tool_calls_from_response(response)
            return LLMResponse(
                content=_content_from_response(response),
                model=str(response_model),
                usage=usage,
                latency_ms=latency_ms,
                response_cost_usd=_response_cost_usd_from_litellm(response),
                tool_calls=tool_calls,
            )

    raise AssertionError("unreachable")  # pragma: no cover
