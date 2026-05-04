"""Integration-style tests for :func:`run_test_case` in platform agent mode."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.enums import AgentMode, SimulatorMode, TestCaseStatus, TurnRole
from app.models.schemas import RunConfig, UserSimulatorConfig
from app.models.test_case import TestCase
from app.services.agent_tool_definitions import canonical_end_call_tool_dict
from app.services.llm import LLMResponse
from app.services.orchestrator import run_test_case


def _platform_test_case() -> TestCase:
    return TestCase(
        id=uuid.uuid4(),
        name="platform-test-case",
        status=TestCaseStatus.ACTIVE,
        first_message="Hello",
        tags=[],
    )


@pytest.mark.asyncio
async def test_run_test_case_platform_uses_agent_simulator_and_tracks_cost() -> None:
    test_case = _platform_test_case()
    config = RunConfig(
        user_simulator=UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=["Thanks, goodbye"],
        ),
        timeout_per_test_case_ms=120_000,
    )
    llm_reply = LLMResponse(
        content="Agent reply here",
        model="openai/gpt-4o-mini",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        latency_ms=42,
        response_cost_usd=0.002,
        tool_calls=None,
    )

    with patch(
        "app.services.agent_simulator.call_llm",
        new_callable=AsyncMock,
        return_value=llm_reply,
    ) as mock_agent_llm:
        result = await run_test_case(
            test_case,
            None,
            config,
            agent_mode=AgentMode.PLATFORM,
            agent_model="gpt-4o-mini",
            agent_provider="openai",
            agent_system_prompt="You are the evaluated agent.",
            agent_tools=None,
        )

    mock_agent_llm.assert_awaited_once()
    roles = [t.role for t in result.transcript]
    assert roles[0] == TurnRole.USER
    assert roles[1] == TurnRole.ASSISTANT
    assert result.transcript[1].content == "Agent reply here"
    assert roles[2] == TurnRole.USER

    assert result.agent_token_usage.get("total_tokens") == 15
    assert result.agent_cost_usd == pytest.approx(0.002)
    assert result.platform_token_usage == {}


@pytest.mark.asyncio
async def test_run_test_case_persona_first_max_turns_ends_on_agent() -> None:
    """max_turns=N should yield N agent turns and end on the agent's last reply,
    without an unanswered trailing user message."""
    test_case = _platform_test_case()
    max_turns = 3
    config = RunConfig(
        max_turns=max_turns,
        user_simulator=UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            # Plenty of scripted replies so the simulator is never the limiter.
            scripted_messages=[f"reply {i}" for i in range(10)],
        ),
        timeout_per_test_case_ms=120_000,
    )
    llm_reply = LLMResponse(
        content="Agent reply",
        model="openai/gpt-4o-mini",
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        latency_ms=1,
        response_cost_usd=0.0,
        tool_calls=None,
    )

    with patch(
        "app.services.agent_simulator.call_llm",
        new_callable=AsyncMock,
        return_value=llm_reply,
    ) as mock_agent_llm:
        result = await run_test_case(
            test_case,
            None,
            config,
            agent_mode=AgentMode.PLATFORM,
            agent_model="gpt-4o-mini",
            agent_provider="openai",
            agent_system_prompt="You are the evaluated agent.",
            agent_tools=None,
        )

    # Exactly max_turns agent calls, no extras.
    assert mock_agent_llm.await_count == max_turns

    roles = [t.role for t in result.transcript]
    # 1 opener + max_turns agent + (max_turns - 1) user replies = 2 * max_turns
    assert len(roles) == 2 * max_turns
    # Conversation ends on the agent's reply, not on an unanswered user turn.
    assert roles[-1] == TurnRole.ASSISTANT
    assert sum(1 for r in roles if r == TurnRole.ASSISTANT) == max_turns


@pytest.mark.asyncio
async def test_run_test_case_platform_stops_after_end_call_tool() -> None:
    test_case = _platform_test_case()
    config = RunConfig(
        user_simulator=UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=["must not run"],
        ),
        timeout_per_test_case_ms=120_000,
    )
    tool_calls = [
        {
            "id": "c_end",
            "type": "function",
            "function": {"name": "end_call", "arguments": "{}"},
        }
    ]
    llm_reply = LLMResponse(
        content="",
        model="openai/gpt-4o-mini",
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        latency_ms=1,
        response_cost_usd=0.0,
        tool_calls=tool_calls,
    )
    term_tool = canonical_end_call_tool_dict()
    with patch(
        "app.services.agent_simulator.call_llm",
        new_callable=AsyncMock,
        return_value=llm_reply,
    ) as mock_agent_llm:
        result = await run_test_case(
            test_case,
            None,
            config,
            agent_mode=AgentMode.PLATFORM,
            agent_model="gpt-4o-mini",
            agent_provider="openai",
            agent_system_prompt="You are the evaluated agent.",
            agent_tools=[term_tool],
        )

    mock_agent_llm.assert_awaited_once()
    assert len(result.transcript) == 2
    assert result.transcript[-1].role == TurnRole.ASSISTANT
    assert result.transcript[-1].tool_calls is not None
    assert result.transcript[-1].tool_calls[0].function.name == "end_call"


@pytest.mark.asyncio
async def test_run_test_case_endpoint_stops_on_end_call_without_scripted_user() -> None:
    from app.models.agent_contract import AgentResponse, ChatMessage
    from app.models.schemas import ToolCall, ToolCallFunction

    test_case = _platform_test_case()
    config = RunConfig(
        user_simulator=UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=["skipped"],
        ),
        timeout_per_test_case_ms=120_000,
    )
    resp = AgentResponse(
        messages=[
            ChatMessage(
                role=TurnRole.ASSISTANT,
                content="Thanks",
                tool_calls=[
                    ToolCall(
                        id="x",
                        function=ToolCallFunction(name="end_call", arguments="{}"),
                    )
                ],
            )
        ]
    )
    term_tool = canonical_end_call_tool_dict()
    with patch(
        "app.services.orchestrator.call_agent",
        new_callable=AsyncMock,
        return_value=(resp, 12),
    ) as mock_call:
        result = await run_test_case(
            test_case,
            "http://agent.test/respond",
            config,
            agent_mode=AgentMode.ENDPOINT,
            agent_tools=[term_tool],
        )

    mock_call.assert_awaited_once()
    assert len(result.transcript) == 2
    assert result.transcript[-1].tool_calls is not None
    assert result.transcript[-1].tool_calls[0].function.name == "end_call"
