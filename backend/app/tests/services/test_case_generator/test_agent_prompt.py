"""Unit tests for test-case AI agent prompts."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import Session

from app.models.enums import TurnRole
from app.models.schemas import ConversationTurn, ToolCall, ToolCallFunction
from app.models.test_case import TestCase as TestCaseRow
from app.services.test_case_generator.agent.context import AgentContext
from app.services.test_case_generator.agent.prompt import (
    _format_transcript,
    build_dynamic_system_message,
    build_static_system_message,
)
from app.services.test_case_generator.agent.schemas import AgentMode
from app.tests.utils.eval import create_test_platform_agent


def test_static_system_mentions_tools() -> None:
    s = build_static_system_message()
    assert "create_test_case" in s
    assert "edit_test_case" in s


def test_static_system_does_not_mention_status() -> None:
    # Lifecycle status is a platform concern; the LLM never sees it.
    s = build_static_system_message()
    assert "status" not in s.lower()
    assert "draft" not in s.lower()


def test_format_transcript_renders_tool_calls_and_results() -> None:
    ts = datetime.now(UTC)
    turns = [
        ConversationTurn(
            index=0,
            role=TurnRole.USER,
            content="What's the weather in Kyiv?",
            timestamp=ts,
        ),
        ConversationTurn(
            index=1,
            role=TurnRole.ASSISTANT,
            content=None,
            tool_calls=[
                ToolCall(
                    id="call_abc",
                    function=ToolCallFunction(
                        name="get_weather",
                        arguments=json.dumps({"city": "Kyiv"}),
                    ),
                    tool_result={"temp_c": 12, "summary": "cloudy"},
                )
            ],
            timestamp=ts,
        ),
        ConversationTurn(
            index=2,
            role=TurnRole.TOOL,
            content='{"temp_c": 12, "summary": "cloudy"}',
            tool_call_id="call_abc",
            timestamp=ts,
        ),
        ConversationTurn(
            index=3,
            role=TurnRole.ASSISTANT,
            content="It's 12°C and cloudy.",
            timestamp=ts,
        ),
    ]
    text = _format_transcript(turns)
    assert "get_weather" in text
    assert '"city": "Kyiv"' in text
    assert "call_abc" in text
    assert "result:" in text
    assert "cloudy" in text
    assert "responding to tool_call id=call_abc" in text


def test_format_transcript_handles_invalid_json_arguments() -> None:
    ts = datetime.now(UTC)
    turns = [
        ConversationTurn(
            index=0,
            role=TurnRole.ASSISTANT,
            content=None,
            tool_calls=[
                ToolCall(
                    id="call_bad",
                    function=ToolCallFunction(
                        name="do_thing",
                        arguments="{not-json}",
                    ),
                )
            ],
            timestamp=ts,
        ),
    ]
    text = _format_transcript(turns)
    assert "do_thing" in text
    assert "{not-json}" in text


def test_dynamic_create_includes_existing_summary(db: Session) -> None:
    agent = create_test_platform_agent(db)
    ctx = AgentContext(
        agent=agent,
        agent_prompt="Be helpful.",
        tools=[],
        available_tags=["normal", "edge-case", "red-team"],
        existing_cases_summary=[
            {"name": "Existing", "tags": ["normal"], "difficulty": "normal"}
        ],
        target_test_case=None,
        transcript=None,
    )
    dyn = build_dynamic_system_message(mode=AgentMode.CREATE, ctx=ctx)
    assert "<existing_test_cases>" in dyn
    assert "Existing" in dyn


def test_dynamic_from_transcript_includes_transcript(db: Session) -> None:
    agent = create_test_platform_agent(db)
    ts = datetime.now(UTC)
    turns = [
        ConversationTurn(
            index=0,
            role=TurnRole.USER,
            content="Hello",
            timestamp=ts,
        ),
        ConversationTurn(
            index=1,
            role=TurnRole.ASSISTANT,
            content="Hi there",
            timestamp=ts,
        ),
    ]
    ctx = AgentContext(
        agent=agent,
        agent_prompt="Sys",
        tools=[],
        available_tags=["normal"],
        existing_cases_summary=None,
        target_test_case=None,
        transcript=turns,
    )
    dyn = build_dynamic_system_message(mode=AgentMode.FROM_TRANSCRIPT, ctx=ctx)
    assert "<transcript>" in dyn
    assert "Hello" in dyn


def test_dynamic_edit_includes_current_case(db: Session) -> None:
    agent = create_test_platform_agent(db)
    tc = TestCaseRow(
        id=uuid4(),
        name="Case A",
        tags=["normal"],
        agent_id=agent.id,
    )
    ctx = AgentContext(
        agent=agent,
        agent_prompt="Sys",
        tools=[],
        available_tags=["normal"],
        existing_cases_summary=None,
        target_test_case=tc,
        transcript=None,
    )
    dyn = build_dynamic_system_message(mode=AgentMode.EDIT, ctx=ctx)
    assert "<current_test_case>" in dyn
    assert "Case A" in dyn
