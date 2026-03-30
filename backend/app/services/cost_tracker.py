"""Token usage aggregation and agent-side token estimation (no DB / I/O)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import litellm

from app.models.agent_contract import ChatMessage

logger = logging.getLogger(__name__)

UsageDict = dict[str, int | bool]
AgentUsageDict = dict[str, int | bool]
PlatformUsageDict = dict[str, int]


def _char_heuristic_token_estimate(text: str) -> int:
    """Rough token count when model-specific counting is unavailable."""
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, len(stripped) // 4)


def _chat_messages_to_dicts(messages: list[ChatMessage]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in messages:
        role = m.role.value
        content = m.content or ""
        if m.tool_calls:
            tc_blob = json.dumps(
                [tc.model_dump(mode="json") for tc in m.tool_calls],
                ensure_ascii=False,
            )
            content = f"{content}\n{tc_blob}"
        out.append({"role": role, "content": content})
    return out


def _count_tokens(model_id: str, message_dicts: list[dict[str, str]]) -> int:
    if not message_dicts:
        return 0
    try:
        return int(litellm.token_counter(model=model_id, messages=message_dicts))
    except Exception:
        logger.debug(
            "token_counter failed for model=%s; using heuristic",
            model_id,
            exc_info=True,
        )
        blob = " ".join(d["content"] for d in message_dicts)
        return _char_heuristic_token_estimate(blob)


def estimate_agent_tokens(
    *,
    prompt_messages: list[ChatMessage] | None = None,
    response_messages: list[ChatMessage],
    agent_system_prompt: str | None = None,
    agent_tools: list[dict[str, Any]] | None = None,
    model: str | None,
    fallback_model: str | None,
) -> AgentUsageDict:
    """Estimate prompt and completion tokens for an agent turn.

    Builds the full prompt context (system prompt + tools schema + conversation
    history) and the completion (response messages) so both sides are counted.
    Falls back to a character heuristic when ``litellm.token_counter`` fails.
    """
    model_id = (model or "").strip() or (fallback_model or "").strip() or "gpt-4o"

    prompt_dicts: list[dict[str, str]] = []
    if agent_system_prompt:
        prompt_dicts.append({"role": "system", "content": agent_system_prompt})
    if agent_tools:
        tools_text = json.dumps(agent_tools, ensure_ascii=False)
        prompt_dicts.append({"role": "system", "content": f"[tools]\n{tools_text}"})
    if prompt_messages:
        prompt_dicts.extend(_chat_messages_to_dicts(prompt_messages))

    completion_dicts = _chat_messages_to_dicts(response_messages)

    prompt_tokens = _count_tokens(model_id, prompt_dicts)
    completion_tokens = _count_tokens(model_id, completion_dicts)

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "estimated": True,
    }


def estimate_agent_cost(
    *,
    model: str | None,
    provider: str | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> float | None:
    """Estimate USD cost for an agent call via ``litellm.completion_cost()``.

    LiteLLM expects a completion-shaped object with ``usage``; it no longer accepts
    raw ``prompt_tokens`` / ``completion_tokens`` keyword arguments.

    Returns ``None`` when the model is unknown to litellm's pricing database.
    """
    if not model:
        return None
    model_id = model.strip()
    if not model_id:
        return None
    if provider and provider.strip() and "/" not in model_id:
        model_id = f"{provider.strip()}/{model_id}"
    completion_response = {
        "model": model_id,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
    try:
        return float(
            litellm.completion_cost(
                completion_response=completion_response,
                model=model_id,
                call_type="acompletion",
            )
        )
    except Exception:
        logger.debug(
            "completion_cost failed for model=%s; skipping agent cost",
            model_id,
            exc_info=True,
        )
        return None


def sum_usage_dicts(*dicts: dict[str, int | bool] | dict[str, int] | None) -> UsageDict:
    """Sum numeric usage keys across dicts; propagate ``estimated`` if any input had it."""
    merged: dict[str, int] = {}
    any_estimated = False
    for d in dicts:
        if not d:
            continue
        if d.get("estimated") is True:
            any_estimated = True
        for k, v in d.items():
            if k == "estimated" or isinstance(v, bool):
                continue
            merged[k] = merged.get(k, 0) + int(v)
    out: UsageDict = {**merged}
    if any_estimated:
        out["estimated"] = True
    return out


def sum_platform_usage_dicts(
    *dicts: dict[str, int] | None,
) -> PlatformUsageDict:
    """Sum platform LLM usage (ints only)."""
    merged: dict[str, int] = {}
    for d in dicts:
        if not d:
            continue
        for k, v in d.items():
            merged[k] = merged.get(k, 0) + int(v)
    return merged


@dataclass
class ScenarioTokenAccumulator:
    """Collects per-scenario agent/platform token dicts and USD costs."""

    _agent_parts: list[AgentUsageDict] = field(default_factory=list)
    _platform_parts: list[PlatformUsageDict] = field(default_factory=list)
    agent_cost_usd: float = 0.0
    platform_cost_usd: float = 0.0

    def add_agent_usage(self, usage: AgentUsageDict | None) -> None:
        if usage:
            self._agent_parts.append(usage)

    def add_agent_cost(self, cost_usd: float | None) -> None:
        if cost_usd is not None:
            self.agent_cost_usd += float(cost_usd)

    def add_platform_usage(self, usage: dict[str, int] | None) -> None:
        if usage:
            self._platform_parts.append(dict(usage))

    def add_platform_cost(self, cost_usd: float | None) -> None:
        if cost_usd is not None:
            self.platform_cost_usd += float(cost_usd)

    @property
    def agent_token_usage(self) -> AgentUsageDict:
        return sum_usage_dicts(*self._agent_parts)

    @property
    def platform_token_usage(self) -> PlatformUsageDict:
        return sum_platform_usage_dicts(*self._platform_parts)
