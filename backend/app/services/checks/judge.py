"""What a judge check uses to ask its language model: one request per call, a fixed
answer shape, the model pinned by the check, and the cost counted for the budget.

A judge check's ``ask`` builds its prompt from the trace with ``render_call`` (or its
own rendering), calls ``ask_judge`` and returns the ``ModelReply``.
"""

import json
import logging

from pydantic import JsonValue

from app.models.trace import ToolCallEvent, Trace, UtteranceEvent
from app.services.checks.base import ModelProvider, ModelReply
from app.services.llm import LLMCallConfig, LLMMessage, call_llm

logger = logging.getLogger(__name__)

# Dollars per million input and output tokens, for models LiteLLM cannot price yet.
_PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}


class JudgeAnswerInvalid(Exception):
    """The judge's answer was not JSON of the shape asked for."""


def render_call(trace: Trace) -> str:
    """The call as numbered lines a judge can cite: who spoke, and each tool call with
    its status. Event ids, not positions, so findings point at the right events."""
    lines = []
    for event in trace.events:
        if isinstance(event, UtteranceEvent):
            lines.append(f"[{event.id}] {event.speaker.value}: {event.text}")
        elif isinstance(event, ToolCallEvent):
            status = event.status.value if event.status else "unknown"
            lines.append(f"[{event.id}] TOOL CALL {event.name} -> {status}")
    return "\n".join(lines)


def _cost(
    model: str, input_tokens: int, output_tokens: int, priced: float | None
) -> float:
    if priced:
        return priced
    prices = _PRICES.get(model.split("/")[-1])
    if prices is None:
        logger.warning("No price known for judge model %s; counted as free", model)
        return 0.0
    return input_tokens * prices[0] / 1e6 + output_tokens * prices[1] / 1e6


async def ask_judge(
    *,
    provider: ModelProvider,
    model: str,
    system: str,
    user: str,
    schema_name: str,
    schema: dict[str, object],
    max_tokens: int = 4000,
) -> ModelReply:
    """Ask the judge once and return its answer, parsed, with what it cost.

    Raises:
        JudgeAnswerInvalid: the answer was not JSON.
        Exception: whatever the model call raised after its retries.
    """
    response = await call_llm(
        [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ],
        config=LLMCallConfig(
            model=model,
            provider=provider.value,
            max_tokens=max_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        ),
    )
    try:
        answer: JsonValue = json.loads(response.content)
    except ValueError as exc:
        msg = "The judge's answer was not JSON"
        raise JudgeAnswerInvalid(msg) from exc
    usage = response.usage or {}
    input_tokens = int(usage.get("prompt_tokens", 0))
    output_tokens = int(usage.get("completion_tokens", 0))
    return ModelReply(
        answer=answer,
        model=response.model or model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=_cost(model, input_tokens, output_tokens, response.response_cost_usd),
        requests=1,
    )
