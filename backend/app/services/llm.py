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

Reasoning-related LiteLLM kwargs (see ``_finalize_litellm_reasoning_kwargs``) are
normalized on every completion: overrides from :attr:`LLMCallConfig.extra` cannot
enable reasoning; reasoning-capable models get ``reasoning_effort=none``.
"""

import json
import logging
import time
from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any, Literal, Protocol, cast

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
from litellm.utils import supports_reasoning
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

# LiteLLM forwards these to provider-specific reasoning / extended-thinking APIs.
# :func:`_finalize_litellm_reasoning_kwargs` removes them from each completion request,
# then sets ``reasoning_effort=none`` when LiteLLM marks the model as reasoning-capable.
_LITELLM_REASONING_KNOB_KEYS: frozenset[str] = frozenset(
    {"reasoning_effort", "thinking"}
)


def _finalize_litellm_reasoning_kwargs(model: str, kwargs: dict[str, object]) -> None:
    """Normalize reasoning controls on merged litellm.acompletion kwargs.

    Drops ``reasoning_effort`` / ``thinking`` so :attr:`LLMCallConfig.extra` cannot
    enable extended reasoning. For models :func:`litellm.utils.supports_reasoning`,
    sets ``reasoning_effort='none'`` so LiteLLM maps providers to minimal/no extended
    reasoning where supported.
    """
    for key in _LITELLM_REASONING_KNOB_KEYS:
        kwargs.pop(key, None)
    try:
        if not supports_reasoning(model=model):
            return
    except Exception:
        logger.debug(
            "supports_reasoning failed for model=%s; skipping reasoning_effort=none",
            model,
            exc_info=True,
        )
        return
    kwargs["reasoning_effort"] = "none"


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
    parallel_tool_calls: bool | None = Field(
        default=None,
        description=(
            "When True, the model may return multiple tool calls in one assistant "
            "message (OpenAI `parallel_tool_calls`). When False, at most one tool "
            "call per turn. Omit to use the provider default."
        ),
    )
    extra: dict[str, LLMExtraValue] = Field(
        default_factory=dict,
        description=(
            "Forwarded as top-level kwargs to litellm.acompletion. Reasoning-related "
            "keys (reasoning_effort, thinking) from extra are dropped when building "
            "the request; reasoning-capable models then receive reasoning_effort=none."
        ),
    )


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


class LLMToolCall(BaseModel):
    """A fully assembled tool call from streaming deltas."""

    id: str
    function_name: str
    arguments: dict[str, Any]


class LLMStreamChunk(BaseModel):
    """A single chunk from a streaming LLM response (text delta)."""

    content: str
    finish_reason: str | None = None


class LLMStreamResult(BaseModel):
    """Final result after the stream is fully consumed (or interrupted)."""

    full_content: str
    tool_calls: list[LLMToolCall]
    usage: dict[str, int] = Field(default_factory=dict)
    model: str
    latency_ms: int
    response_cost_usd: float | None = None


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
            raw_dump = dumped(mode="json")
            if isinstance(raw_dump, dict):
                out.append(raw_dump)
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


class _ToolCallAccumulator:
    """Accumulates OpenAI-style tool_call deltas across streaming chunks."""

    def __init__(self) -> None:
        self._slots: dict[int, dict[str, str]] = {}

    def process_delta_list(self, deltas: object) -> None:
        if not deltas or not isinstance(deltas, list):
            return
        for d in deltas:
            self._process_one_delta(d)

    def _process_one_delta(self, d: object) -> None:
        idx_raw = getattr(d, "index", None)
        if idx_raw is None and isinstance(d, dict):
            idx_raw = d.get("index")
        idx = 0 if idx_raw is None else int(idx_raw)
        slot = self._slots.setdefault(idx, {"id": "", "name": "", "arguments": ""})

        tid = getattr(d, "id", None)
        if tid is None and isinstance(d, dict):
            tid = d.get("id")
        if tid:
            slot["id"] = str(tid)

        fn = getattr(d, "function", None)
        if fn is None and isinstance(d, dict):
            fn = d.get("function")
        if fn is None:
            return
        name = getattr(fn, "name", None)
        args = getattr(fn, "arguments", None)
        if name is None and isinstance(fn, dict):
            name = fn.get("name")
        if args is None and isinstance(fn, dict):
            args = fn.get("arguments")
        if name:
            slot["name"] += str(name)
        if args:
            slot["arguments"] += str(args)

    def finalize(self) -> list[LLMToolCall]:
        out: list[LLMToolCall] = []
        for idx in sorted(self._slots.keys()):
            slot = self._slots[idx]
            name = slot["name"].strip()
            if not name:
                continue
            raw_args = slot["arguments"] or "{}"
            try:
                parsed = json.loads(raw_args)
            except json.JSONDecodeError as e:
                logger.warning(
                    "Malformed tool call arguments for stream index %s: %s",
                    idx,
                    e,
                )
                continue
            if not isinstance(parsed, dict):
                logger.warning(
                    "Tool call arguments for stream index %s are not a JSON object; skipping",
                    idx,
                )
                continue
            out.append(
                LLMToolCall(
                    id=slot["id"] or f"call_{idx}",
                    function_name=name,
                    arguments=parsed,
                )
            )
        return out


async def _acompletion_once(
    *,
    model: str,
    message_dicts: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    temperature: float | None,
    max_tokens: int | None,
    timeout: float | None,
    response_format: dict[str, object] | None,
    parallel_tool_calls: bool | None,
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
    if parallel_tool_calls is not None:
        kwargs["parallel_tool_calls"] = parallel_tool_calls
    for k, v in extra.items():
        if v is not None:
            kwargs[k] = v
    _finalize_litellm_reasoning_kwargs(model, kwargs)
    return await litellm.acompletion(**cast(Any, kwargs))


async def _acompletion_stream_once(
    *,
    model: str,
    message_dicts: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    temperature: float | None,
    max_tokens: int | None,
    timeout: float | None,
    response_format: dict[str, object] | None,
    parallel_tool_calls: bool | None,
    extra: dict[str, LLMExtraValue],
) -> object:
    kwargs: dict[str, object] = {
        "model": model,
        "messages": message_dicts,
        "stream": True,
        "stream_options": {"include_usage": True},
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
    if parallel_tool_calls is not None:
        kwargs["parallel_tool_calls"] = parallel_tool_calls
    for k, v in extra.items():
        if v is not None:
            kwargs[k] = v
    _finalize_litellm_reasoning_kwargs(model, kwargs)
    return await litellm.acompletion(**cast(Any, kwargs))


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
    parallel_tool_calls = c.parallel_tool_calls

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
                parallel_tool_calls=parallel_tool_calls,
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


def _delta_from_stream_chunk(chunk: object) -> tuple[object | None, str | None]:
    """Return (delta, finish_reason) from a streaming chunk, if any."""
    choices = getattr(chunk, "choices", None)
    if not choices:
        return None, None
    first = choices[0]
    finish = getattr(first, "finish_reason", None)
    delta = getattr(first, "delta", None)
    return delta, finish if isinstance(finish, str) else None


async def call_llm_stream(
    messages: list[LLMMessage],
    config: LLMCallConfig | None = None,
    *,
    app_settings: LLMSettingsView | None = None,
) -> AsyncGenerator[LLMStreamChunk | LLMStreamResult, None]:
    """Streaming variant of :func:`call_llm`.

    Yields :class:`LLMStreamChunk` for each non-empty text delta. Tool call
    fragments are accumulated and not yielded. After the stream completes,
    yields a single :class:`LLMStreamResult` with full text, parsed tool
    calls, usage, and timing. On mid-stream errors, yields a partial result
    with accumulated text and empty tool calls.
    """
    app_settings = app_settings or settings
    resolved_model, _ = _merge_effective_model_provider(config, app_settings)
    c = config or LLMCallConfig()

    temperature = c.temperature
    max_tokens = c.max_tokens
    timeout = c.timeout_seconds
    response_format = c.response_format
    extra = dict(c.extra)
    tools = c.tools
    parallel_tool_calls = c.parallel_tool_calls

    message_dicts = [_llm_message_to_litellm_dict(m) for m in messages]
    started = time.perf_counter()

    stream: object | None = None
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
            stream = await _acompletion_stream_once(
                model=resolved_model,
                message_dicts=message_dicts,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                response_format=response_format,
                parallel_tool_calls=parallel_tool_calls,
                extra=extra,
            )
            break

    if stream is None:
        raise AssertionError("unreachable")  # pragma: no cover

    full_parts: list[str] = []
    accumulator = _ToolCallAccumulator()
    usage: dict[str, int] = {}
    response_model = resolved_model
    response_cost: float | None = None

    stream_iter = cast(AsyncIterable[object], stream)
    try:
        async for chunk in stream_iter:
            m = getattr(chunk, "model", None)
            if m:
                response_model = str(m)
            usage_obj = getattr(chunk, "usage", None)
            if usage_obj is not None:
                usage = _usage_to_dict(usage_obj)
            cost = _response_cost_usd_from_litellm(chunk)
            if cost is not None:
                response_cost = cost

            delta, fr = _delta_from_stream_chunk(chunk)
            if delta is None:
                continue

            text = getattr(delta, "content", None)
            if isinstance(text, str) and text:
                full_parts.append(text)
                yield LLMStreamChunk(content=text, finish_reason=fr)

            tool_deltas = getattr(delta, "tool_calls", None)
            if tool_deltas:
                accumulator.process_delta_list(tool_deltas)
    except Exception as exc:
        logger.warning("LLM stream interrupted: %s: %s", type(exc).__name__, exc)
        latency_ms = int((time.perf_counter() - started) * 1000)
        yield LLMStreamResult(
            full_content="".join(full_parts),
            tool_calls=[],
            usage=usage,
            model=response_model,
            latency_ms=latency_ms,
            response_cost_usd=response_cost,
        )
        return

    latency_ms = int((time.perf_counter() - started) * 1000)
    yield LLMStreamResult(
        full_content="".join(full_parts),
        tool_calls=accumulator.finalize(),
        usage=usage,
        model=response_model,
        latency_ms=latency_ms,
        response_cost_usd=response_cost,
    )


async def collect_stream(
    stream: AsyncGenerator[LLMStreamChunk | LLMStreamResult, None],
) -> LLMStreamResult:
    """Consume a stream from :func:`call_llm_stream`; return the final result only."""
    final: LLMStreamResult | None = None
    async for item in stream:
        if isinstance(item, LLMStreamResult):
            final = item
    if final is None:
        msg = "Stream ended without an LLMStreamResult"
        raise RuntimeError(msg)
    return final
