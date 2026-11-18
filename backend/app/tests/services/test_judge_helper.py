"""The judge helper for judge checks: one request, a fixed answer shape, its cost.
The model is faked."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.trace import Trace
from app.services.checks.base import ModelProvider
from app.services.checks.judge import JudgeAnswerInvalid, ask_judge, render_call
from app.services.llm import LLMResponse

SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


async def _ask(content: str, cost: float | None = None):
    response = LLMResponse(
        content=content,
        model="claude-haiku-5-5",
        usage={"prompt_tokens": 1_000_000, "completion_tokens": 100_000},
        response_cost_usd=cost,
    )
    with patch(
        "app.services.checks.judge.call_llm",
        new_callable=AsyncMock,
        return_value=response,
    ) as mock:
        reply = await ask_judge(
            provider=ModelProvider.ANTHROPIC,
            model="claude-haiku-5-5",
            system="s",
            user="u",
            schema_name="x",
            schema=SCHEMA,
        )
    return reply, mock


async def test_answer_and_cost_from_the_price_table() -> None:
    reply, mock = await _ask('{"ok": true}')
    assert reply.answer == {"ok": True}
    # $0.10 per 1M input, $0.50 per 1M output.
    assert reply.cost_usd == pytest.approx(0.10 + 0.05)
    config = mock.await_args.kwargs["config"]
    assert (config.model, config.provider) == ("claude-haiku-5-5", "anthropic")
    assert config.response_format["json_schema"]["schema"] == SCHEMA


async def test_litellm_cost_wins_when_it_has_one() -> None:
    reply, _ = await _ask('{"ok": false}', cost=0.42)
    assert reply.cost_usd == pytest.approx(0.42)


async def test_empty_answer_is_invalid() -> None:
    with pytest.raises(JudgeAnswerInvalid):
        await _ask("")


async def test_malformed_answer_is_invalid() -> None:
    with pytest.raises(JudgeAnswerInvalid):
        await _ask("not json {")


async def test_a_timeout_is_raised_for_the_runner_to_record() -> None:
    with (
        patch(
            "app.services.checks.judge.call_llm",
            new_callable=AsyncMock,
            side_effect=TimeoutError(),
        ),
        pytest.raises(TimeoutError),
    ):
        await ask_judge(
            provider=ModelProvider.ANTHROPIC,
            model="claude-haiku-5-5",
            system="s",
            user="u",
            schema_name="x",
            schema=SCHEMA,
        )


def test_render_call_numbers_lines_by_event_id() -> None:
    trace = Trace.model_validate(
        {
            "provider": "invented",
            "external_id": "c",
            "started_at": "2026-10-01T12:00:00Z",
            "events": [
                {"type": "utterance", "id": "u1", "speaker": "agent", "text": "Hi"},
                {"type": "tool_call", "id": "t1", "name": "book", "status": "ok"},
            ],
        }
    )
    assert render_call(trace) == "[u1] agent: Hi\n[t1] TOOL CALL book -> ok"
