"""Integration-style tests for :func:`run_test_case` in platform agent mode."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.enums import AgentMode, SimulatorMode, TestCaseStatus, TurnRole
from app.models.schemas import RunConfig, UserSimulatorConfig
from app.models.test_case import TestCase
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
