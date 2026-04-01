"""Integration-style tests for :func:`run_scenario` in platform agent mode."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.enums import AgentMode, ScenarioStatus, SimulatorMode, TurnRole
from app.models.scenario import Scenario
from app.models.schemas import RunConfig, UserSimulatorConfig
from app.services.llm import LLMResponse
from app.services.orchestrator import run_scenario


def _platform_scenario() -> Scenario:
    return Scenario(
        id=uuid.uuid4(),
        name="platform-scenario",
        status=ScenarioStatus.ACTIVE,
        initial_message="Hello",
        max_turns=1,
        tags=[],
    )


@pytest.mark.asyncio
async def test_run_scenario_platform_uses_agent_simulator_and_tracks_cost() -> None:
    scenario = _platform_scenario()
    config = RunConfig(
        user_simulator=UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=["Thanks, goodbye"],
        ),
        timeout_per_scenario_ms=120_000,
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
        result = await run_scenario(
            scenario,
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
