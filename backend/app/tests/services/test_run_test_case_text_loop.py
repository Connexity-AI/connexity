"""Integration-style tests for the shared text loop's ``run_text_test_case``.

Driven through the custom endpoint runtime with the HTTP call patched, so the
loop (turn ordering, max_turns, terminating tools, usage tracking) is exercised
without a network.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.agent_contract import AgentResponse, ChatMessage, TokenUsage
from app.models.enums import AgentMode, SimulatorMode, TestCaseStatus, TurnRole
from app.models.schemas import (
    CustomEndpointRuntimeConfig,
    RunConfig,
    ToolCall,
    ToolCallFunction,
    UserSimulatorConfig,
)
from app.models.test_case import TestCase
from app.services.agent_tool_definitions import canonical_end_call_tool_dict
from app.services.eval_runtimes.text.base import TextAgentTurnConfig
from app.services.eval_runtimes.text.custom_endpoint import CustomEndpointRuntime

_ENDPOINT_URL = "http://agent.test/respond"


def _test_case() -> TestCase:
    return TestCase(
        id=uuid.uuid4(),
        name="text-loop-test-case",
        status=TestCaseStatus.ACTIVE,
        first_message="Hello",
        tags=[],
    )


def _run_config(
    *, scripted_messages: list[str], max_turns: int | None = None
) -> RunConfig:
    return RunConfig(
        max_turns=max_turns,
        user_simulator=UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=scripted_messages,
        ),
        timeout_per_test_case_ms=120_000,
        runtime=CustomEndpointRuntimeConfig(url=_ENDPOINT_URL),
    )


def _agent_config(tools: list[dict] | None = None) -> TextAgentTurnConfig:
    return TextAgentTurnConfig(
        endpoint_url=_ENDPOINT_URL,
        agent_mode=AgentMode.ENDPOINT,
        tools=tools,
    )


def _end_call_response() -> AgentResponse:
    return AgentResponse(
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


@pytest.mark.asyncio
async def test_run_test_case_tracks_reported_agent_usage() -> None:
    resp = AgentResponse(
        messages=[ChatMessage(role=TurnRole.ASSISTANT, content="Agent reply here")],
        model="gpt-4o-mini",
        provider="openai",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )
    with patch.object(
        CustomEndpointRuntime,
        "_post_agent_request",
        new_callable=AsyncMock,
        return_value=(resp, 42),
    ) as mock_call:
        result = await CustomEndpointRuntime().run_text_test_case(
            _test_case(),
            _agent_config(),
            _run_config(scripted_messages=["Thanks, goodbye"], max_turns=1),
        )

    mock_call.assert_awaited_once()
    roles = [t.role for t in result.transcript]
    assert roles == [TurnRole.USER, TurnRole.ASSISTANT]
    assert result.transcript[1].content == "Agent reply here"
    assert result.agent_token_usage.get("total_tokens") == 15
    assert result.platform_token_usage == {}


@pytest.mark.asyncio
async def test_run_test_case_persona_first_max_turns_ends_on_agent() -> None:
    """max_turns=N should yield N agent turns and end on the agent's last reply,
    without an unanswered trailing user message."""
    max_turns = 3
    resp = AgentResponse(
        messages=[ChatMessage(role=TurnRole.ASSISTANT, content="Agent reply")]
    )
    with patch.object(
        CustomEndpointRuntime,
        "_post_agent_request",
        new_callable=AsyncMock,
        return_value=(resp, 1),
    ) as mock_call:
        result = await CustomEndpointRuntime().run_text_test_case(
            _test_case(),
            _agent_config(),
            # Plenty of scripted replies so the simulator is never the limiter.
            _run_config(
                scripted_messages=[f"reply {i}" for i in range(10)],
                max_turns=max_turns,
            ),
        )

    # Exactly max_turns agent calls, no extras.
    assert mock_call.await_count == max_turns

    roles = [t.role for t in result.transcript]
    # 1 opener + max_turns agent + (max_turns - 1) user replies = 2 * max_turns
    assert len(roles) == 2 * max_turns
    # Conversation ends on the agent's reply, not on an unanswered user turn.
    assert roles[-1] == TurnRole.ASSISTANT
    assert sum(1 for r in roles if r == TurnRole.ASSISTANT) == max_turns


@pytest.mark.asyncio
async def test_run_test_case_stops_on_end_call_without_scripted_user() -> None:
    with patch.object(
        CustomEndpointRuntime,
        "_post_agent_request",
        new_callable=AsyncMock,
        return_value=(_end_call_response(), 12),
    ) as mock_call:
        result = await CustomEndpointRuntime().run_text_test_case(
            _test_case(),
            _agent_config(tools=[canonical_end_call_tool_dict()]),
            _run_config(scripted_messages=["skipped"]),
        )

    mock_call.assert_awaited_once()
    assert len(result.transcript) == 2
    assert result.transcript[-1].role == TurnRole.ASSISTANT
    assert result.transcript[-1].tool_calls is not None
    assert result.transcript[-1].tool_calls[0].function.name == "end_call"
