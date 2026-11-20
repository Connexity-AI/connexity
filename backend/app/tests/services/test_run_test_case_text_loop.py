"""Integration-style tests for the shared text loop's ``run_text_test_case``.

Driven through a runtime whose agent answers from a script, so the loop (turn
ordering, max_turns, terminating tools, usage tracking) is exercised without a
network.
"""

import uuid
from typing import Any

import pytest

from app.models.agent_contract import AgentResponse, ChatMessage, TokenUsage
from app.models.enums import (
    AgentMode,
    RunMode,
    SimulatorMode,
    TestCaseStatus,
    TextRuntimeKind,
    TurnRole,
)
from app.models.schemas import (
    RetellRuntimeConfig,
    RunConfig,
    ToolCall,
    ToolCallFunction,
    UserSimulatorConfig,
)
from app.models.test_case import TestCase
from app.services.eval_runtimes.text.base import (
    TextAgentTurnConfig,
    TextAgentTurnContext,
    TextRuntimeBase,
)

_END_CALL_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {"name": "end_call", "description": "End the call."},
    "platform_config": {"terminating": True},
}


class _ScriptedAgentRuntime(TextRuntimeBase):
    """A text runtime whose agent gives the same answer every turn."""

    MODE = RunMode.TEXT
    KIND = TextRuntimeKind.RETELL
    LABEL = "scripted"
    DESCRIPTION = "test double"

    def __init__(self, response: AgentResponse) -> None:
        self.response = response
        self.turns = 0

    def supported_for_platform(self, platform: object) -> bool:
        return True

    def validate_config(
        self, runtime_config: object, agent: object, session: object
    ) -> None:
        return None

    async def test_connection(
        self, runtime_config: object, agent: object, session: object
    ) -> Any:
        raise NotImplementedError

    def build_text_agent_config(
        self, runtime_config: object, args: object, session: object
    ) -> TextAgentTurnConfig:
        raise NotImplementedError

    async def do_agent_turn(self, context: TextAgentTurnContext) -> bool:
        self.turns += 1
        usage = self.response.usage
        if usage is not None and usage.total_tokens is not None:
            context.accumulator.add_agent_usage({"total_tokens": usage.total_tokens})
        self.append_wire_messages_to_transcript(context.transcript, self.response, 1)
        return True


def _test_case() -> TestCase:
    return TestCase(
        id=uuid.uuid4(),
        name="text-loop-test-case",
        status=TestCaseStatus.ACTIVE,
        first_message="Hello",
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
        runtime=RetellRuntimeConfig(),
    )


def _agent_config(tools: list[dict[str, Any]] | None = None) -> TextAgentTurnConfig:
    return TextAgentTurnConfig(
        endpoint_url=None,
        agent_mode=AgentMode.PLATFORM,
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
    runtime = _ScriptedAgentRuntime(
        AgentResponse(
            messages=[ChatMessage(role=TurnRole.ASSISTANT, content="Agent reply here")],
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )
    )
    result = await runtime.run_text_test_case(
        _test_case(),
        _agent_config(),
        _run_config(scripted_messages=["Thanks, goodbye"], max_turns=1),
    )

    assert runtime.turns == 1
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
    runtime = _ScriptedAgentRuntime(
        AgentResponse(
            messages=[ChatMessage(role=TurnRole.ASSISTANT, content="Agent reply")]
        )
    )
    result = await runtime.run_text_test_case(
        _test_case(),
        _agent_config(),
        # Plenty of scripted replies so the simulator is never the limiter.
        _run_config(
            scripted_messages=[f"reply {i}" for i in range(10)],
            max_turns=max_turns,
        ),
    )

    # Exactly max_turns agent calls, no extras.
    assert runtime.turns == max_turns

    roles = [t.role for t in result.transcript]
    # 1 opener + max_turns agent + (max_turns - 1) user replies = 2 * max_turns
    assert len(roles) == 2 * max_turns
    # Conversation ends on the agent's reply, not on an unanswered user turn.
    assert roles[-1] == TurnRole.ASSISTANT
    assert sum(1 for r in roles if r == TurnRole.ASSISTANT) == max_turns


@pytest.mark.asyncio
async def test_run_test_case_stops_on_end_call_without_scripted_user() -> None:
    runtime = _ScriptedAgentRuntime(_end_call_response())
    result = await runtime.run_text_test_case(
        _test_case(),
        _agent_config(tools=[_END_CALL_TOOL]),
        _run_config(scripted_messages=["skipped"]),
    )

    assert runtime.turns == 1
    assert len(result.transcript) == 2
    assert result.transcript[-1].role == TurnRole.ASSISTANT
    assert result.transcript[-1].tool_calls is not None
    assert result.transcript[-1].tool_calls[0].function.name == "end_call"
