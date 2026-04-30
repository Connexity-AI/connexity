"""Unit tests for TestCaseAgent core (mocked LLM)."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlmodel import Session

from app.models.test_case import TestCase as TestCaseRow
from app.services.llm import LLMResponse
from app.services.test_case_generator.interactive.context import AgentContext
from app.services.test_case_generator.interactive.core import (
    TestCaseAgent,
    TestCaseAgentInput,
)
from app.services.test_case_generator.interactive.schemas import AgentMode
from app.tests.utils.eval import create_test_platform_agent


def _tc_args(*, name: str = "Generated") -> dict:
    return {
        "name": name,
        "tags": ["normal"],
        "difficulty": "normal",
        "persona_context": (
            "[Persona type]\n"
            "Test user\n"
            "[Description]\n"
            "A user exercising the agent in a realistic scenario.\n"
            "[Behavioral instructions]\n"
            "Reveal details naturally and cooperate with the agent."
        ),
        "first_message": "Hello",
    }


def _tool_dict(name: str, args: dict) -> dict:
    return {
        "id": "call_1",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


@pytest.mark.asyncio
async def test_run_create_mode(db: Session) -> None:
    agent = create_test_platform_agent(db)
    ctx = AgentContext(
        agent=agent,
        agent_prompt="Sys",
        tools=[],
        available_tags=["normal", "edge-case", "red-team"],
        existing_cases_summary=None,
        target_test_case=None,
        transcript=None,
    )
    mock_resp = LLMResponse(
        content="",
        model="gpt-4o",
        usage={"total_tokens": 10},
        latency_ms=5,
        tool_calls=[
            _tool_dict("create_test_case", _tc_args(name="One")),
            _tool_dict("create_test_case", _tc_args(name="Two")),
        ],
    )
    with patch(
        "app.services.test_case_generator.interactive.core.call_llm",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        out = await TestCaseAgent(
            TestCaseAgentInput(
                mode=AgentMode.CREATE,
                user_message="Make two cases",
                context=ctx,
            )
        ).run()
    assert len(out.created) == 2
    assert out.created[0].name == "One"
    assert out.edited is None


@pytest.mark.asyncio
async def test_run_from_transcript_allows_multiple_creates(db: Session) -> None:
    agent = create_test_platform_agent(db)
    ctx = AgentContext(
        agent=agent,
        agent_prompt="Sys",
        tools=[],
        available_tags=["normal"],
        existing_cases_summary=None,
        target_test_case=None,
        transcript=[],
    )
    mock_resp = LLMResponse(
        content="",
        model="gpt-4o",
        usage={},
        latency_ms=1,
        tool_calls=[
            _tool_dict("create_test_case", _tc_args(name="First")),
            _tool_dict("create_test_case", _tc_args(name="Second")),
        ],
    )
    with patch(
        "app.services.test_case_generator.interactive.core.call_llm",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        out = await TestCaseAgent(
            TestCaseAgentInput(
                mode=AgentMode.FROM_TRANSCRIPT,
                user_message="Convert",
                context=ctx,
            )
        ).run()
    assert len(out.created) == 2
    assert [tc.name for tc in out.created] == ["First", "Second"]
    assert out.edited is None


@pytest.mark.asyncio
async def test_run_edit_mode(db: Session) -> None:
    plat = create_test_platform_agent(db)
    now = datetime.now(UTC)
    tc = TestCaseRow(
        id=uuid4(),
        name="Before",
        tags=["test"],
        agent_id=plat.id,
        created_at=now,
        updated_at=now,
    )
    ctx = AgentContext(
        agent=plat,
        agent_prompt="Sys",
        tools=[],
        available_tags=["normal"],
        existing_cases_summary=None,
        target_test_case=tc,
        transcript=None,
    )
    args = _tc_args(name="After")
    mock_resp = LLMResponse(
        content="",
        model="gpt-4o",
        usage={},
        latency_ms=1,
        tool_calls=[_tool_dict("edit_test_case", args)],
    )
    with patch(
        "app.services.test_case_generator.interactive.core.call_llm",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        out = await TestCaseAgent(
            TestCaseAgentInput(
                mode=AgentMode.EDIT,
                user_message="Rename",
                context=ctx,
            )
        ).run()
    assert out.edited is not None
    assert out.edited.name == "After"
    assert out.created == []


@pytest.mark.asyncio
async def test_run_repairs_invalid_create_payload(db: Session) -> None:
    agent = create_test_platform_agent(db)
    ctx = AgentContext(
        agent=agent,
        agent_prompt="Sys",
        tools=[],
        available_tags=["normal"],
        existing_cases_summary=None,
        target_test_case=None,
        transcript=None,
    )
    invalid_args = dict(_tc_args(name="Broken"), persona_context="A test persona.")
    first_resp = LLMResponse(
        content="",
        model="gpt-4o",
        usage={"total_tokens": 10},
        latency_ms=5,
        tool_calls=[_tool_dict("create_test_case", invalid_args)],
    )
    repair_resp = LLMResponse(
        content="",
        model="gpt-4o",
        usage={"total_tokens": 7},
        latency_ms=8,
        tool_calls=[_tool_dict("create_test_case", _tc_args(name="Fixed"))],
    )
    mock_call = AsyncMock(side_effect=[first_resp, repair_resp])
    with patch(
        "app.services.test_case_generator.interactive.core.call_llm",
        new=mock_call,
    ):
        out = await TestCaseAgent(
            TestCaseAgentInput(
                mode=AgentMode.CREATE,
                user_message="Make one case",
                context=ctx,
            )
        ).run()

    assert [tc.name for tc in out.created] == ["Fixed"]
    assert out.latency_ms == 13
    assert out.token_usage == {"total_tokens": 17}
    assert mock_call.await_count == 2


@pytest.mark.asyncio
async def test_run_merges_partial_create_repair(db: Session) -> None:
    agent = create_test_platform_agent(db)
    ctx = AgentContext(
        agent=agent,
        agent_prompt="Sys",
        tools=[],
        available_tags=["normal"],
        existing_cases_summary=None,
        target_test_case=None,
        transcript=None,
    )
    invalid_args = _tc_args(name="This Name Is Much Too Long For Validation")
    first_resp = LLMResponse(
        content="",
        model="gpt-4o",
        usage={"total_tokens": 10},
        latency_ms=5,
        tool_calls=[
            _tool_dict("create_test_case", _tc_args(name="Kept")),
            _tool_dict("create_test_case", invalid_args),
        ],
    )
    repair_resp = LLMResponse(
        content="",
        model="gpt-4o",
        usage={"total_tokens": 7},
        latency_ms=8,
        tool_calls=[_tool_dict("create_test_case", _tc_args(name="Fixed"))],
    )
    mock_call = AsyncMock(side_effect=[first_resp, repair_resp])
    with patch(
        "app.services.test_case_generator.interactive.core.call_llm",
        new=mock_call,
    ):
        out = await TestCaseAgent(
            TestCaseAgentInput(
                mode=AgentMode.CREATE,
                user_message="Make two cases",
                context=ctx,
            )
        ).run()

    assert [tc.name for tc in out.created] == ["Kept", "Fixed"]
    assert out.latency_ms == 13
    assert mock_call.await_count == 2
