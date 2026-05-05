"""Tests for :mod:`app.services.agent_simulator` with mocked ``call_llm``."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.agent_contract import ChatMessage
from app.models.enums import TurnRole
from app.models.schemas import AgentSimulatorConfig
from app.services.agent_simulator import AgentSimulator
from app.services.agent_tool_definitions import canonical_end_call_tool_dict
from app.services.llm import LLMCallConfig, LLMMessage, LLMResponse
from app.services.tool_executor import SyntheticToolExecutor, ToolExecutor


def _llm_resp(
    *,
    content: str = "",
    tool_calls: list[dict[str, object]] | None = None,
    usage: dict[str, int] | None = None,
    model: str = "openai/gpt-4o-mini",
    latency_ms: int = 5,
    cost: float | None = 0.0001,
) -> LLMResponse:
    return LLMResponse(
        content=content,
        model=model,
        usage=usage or {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        latency_ms=latency_ms,
        response_cost_usd=cost,
        tool_calls=tool_calls,
    )


@pytest.mark.asyncio
async def test_generate_response_plain_assistant_reply() -> None:
    sim = AgentSimulator(
        system_prompt="You are the agent.",
        tools=None,
        agent_model="gpt-4o-mini",
        agent_provider="openai",
    )
    with patch(
        "app.services.agent_simulator.call_llm",
        new_callable=AsyncMock,
        return_value=_llm_resp(content="Hello from agent"),
    ) as mock_llm:
        out = await sim.generate_response(
            [ChatMessage(role=TurnRole.USER, content="Hi")]
        )

    mock_llm.assert_awaited_once()
    call_kw = mock_llm.await_args.kwargs
    msgs = mock_llm.await_args.args[0]
    assert call_kw["config"].model == "gpt-4o-mini"
    assert call_kw["config"].provider == "openai"
    assert msgs[0] == LLMMessage(role="system", content="You are the agent.")
    assert msgs[1].role == "user"
    assert msgs[1].content == "Hi"

    assert len(out.messages) == 1
    assert out.messages[0].role == TurnRole.ASSISTANT
    assert out.messages[0].content == "Hello from agent"
    assert out.token_usage["total_tokens"] == 2
    assert out.latency_ms == 5
    assert out.cost_usd == pytest.approx(0.0001)
    assert out.model == "gpt-4o-mini"
    assert out.provider == "openai"


@pytest.mark.asyncio
async def test_generate_response_tool_round_then_final_text() -> None:
    tool_calls = [
        {
            "id": "call_abc",
            "type": "function",
            "function": {"name": "lookup", "arguments": '{"q":"x"}'},
        }
    ]
    first = _llm_resp(content="", tool_calls=tool_calls)
    second = _llm_resp(content="Here is the answer.", tool_calls=None)

    sim = AgentSimulator(
        system_prompt="Sys",
        tools=[{"type": "function", "function": {"name": "lookup"}}],
        agent_model="gpt-4o-mini",
        agent_provider=None,
    )

    with patch(
        "app.services.agent_simulator.call_llm",
        new_callable=AsyncMock,
        side_effect=[first, second],
    ) as mock_llm:
        out = await sim.generate_response(
            [ChatMessage(role=TurnRole.USER, content="Search please")]
        )

    assert mock_llm.await_count == 2
    trail = mock_llm.await_args_list[1].args[0]
    assert any(m.role == "tool" and m.tool_call_id == "call_abc" for m in trail)

    assert len(out.messages) == 3
    assert out.messages[0].role == TurnRole.ASSISTANT
    assert out.messages[0].tool_calls is not None
    assert out.messages[0].tool_calls[0].function.name == "lookup"
    assert out.messages[1].role == TurnRole.TOOL
    assert "simulated" in (out.messages[1].content or "")
    assert out.messages[2].role == TurnRole.ASSISTANT
    assert out.messages[2].content == "Here is the answer."
    assert out.token_usage["total_tokens"] == 4


@pytest.mark.asyncio
async def test_config_overrides_agent_model_and_provider() -> None:
    sim = AgentSimulator(
        system_prompt="S",
        tools=None,
        agent_model="base-model",
        agent_provider="openai",
        config=AgentSimulatorConfig(model="override-model", provider="anthropic"),
    )
    with patch(
        "app.services.agent_simulator.call_llm",
        new_callable=AsyncMock,
        return_value=_llm_resp(model="anthropic/override-model"),
    ) as mock_llm:
        await sim.generate_response([ChatMessage(role=TurnRole.USER, content="x")])

    cfg = mock_llm.await_args.kwargs["config"]
    assert isinstance(cfg, LLMCallConfig)
    assert cfg.model == "override-model"
    assert cfg.provider == "anthropic"


@pytest.mark.asyncio
async def test_custom_tool_executor() -> None:
    class CustomExec(ToolExecutor):
        async def execute(
            self, tool_name: str, tool_call_id: str, arguments: str
        ) -> str:
            return '{"custom": true, "tool": "' + tool_name + '"}'

    tool_calls = [
        {
            "id": "t1",
            "type": "function",
            "function": {"name": "foo", "arguments": "{}"},
        }
    ]
    first = _llm_resp(content="", tool_calls=tool_calls)
    second = _llm_resp(content="ok", tool_calls=None)

    sim = AgentSimulator(
        system_prompt="S",
        tools=None,
        agent_model="m",
        agent_provider=None,
        tool_executor=CustomExec(),
    )
    with patch(
        "app.services.agent_simulator.call_llm",
        new_callable=AsyncMock,
        side_effect=[first, second],
    ):
        out = await sim.generate_response(
            [ChatMessage(role=TurnRole.USER, content="go")]
        )

    assert '"custom": true' in (out.messages[1].content or "")


@pytest.mark.asyncio
async def test_generate_response_terminating_tool_short_circuits_no_executor_round() -> (
    None
):
    tool_calls = [
        {
            "id": "c_end",
            "type": "function",
            "function": {"name": "end_call", "arguments": "{}"},
        }
    ]
    llm_only = _llm_resp(content="", tool_calls=tool_calls)

    sim = AgentSimulator(
        system_prompt="Sys",
        tools=[canonical_end_call_tool_dict()],
        agent_model="gpt-4o-mini",
        agent_provider=None,
    )

    with patch(
        "app.services.agent_simulator.call_llm",
        new_callable=AsyncMock,
        return_value=llm_only,
    ) as mock_llm:
        out = await sim.generate_response(
            [ChatMessage(role=TurnRole.USER, content="Bye")]
        )

    mock_llm.assert_awaited_once()
    assert len(out.messages) == 1
    assert out.messages[0].role == TurnRole.ASSISTANT
    assert out.messages[0].tool_calls is not None
    assert out.messages[0].tool_calls[0].function.name == "end_call"


@pytest.mark.asyncio
async def test_synthetic_tool_executor_returns_json() -> None:
    ex = SyntheticToolExecutor()
    raw = await ex.execute("any", "id", "{}")
    assert "simulated" in raw
    assert "Tool not executed" in raw
