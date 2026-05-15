"""Retell runtime placeholder behavior."""

import uuid
from unittest.mock import MagicMock

import pytest

from app.models.agent import Agent
from app.models.enums import AgentMode, Platform
from app.models.schemas import RetellRuntimeConfig, RunConfig
from app.services.eval_runtimes import AgentSnapshot, RunSnapshot
from app.services.eval_runtimes.base import RuntimeRunArgs
from app.services.eval_runtimes.text.retell import (
    RetellRuntime,
    RetellRuntimeNotImplementedError,
)


def _make_agent(platform: Platform | None = Platform.RETELL) -> Agent:
    return Agent(
        id=uuid.uuid4(),
        name="agent",
        mode=AgentMode.PLATFORM,
        endpoint_url=None,
        platform=platform,
        integration_id=uuid.uuid4(),
        platform_agent_id="retell_agent_123",
    )


def test_supported_for_platform_only_retell() -> None:
    runtime = RetellRuntime()
    assert runtime.supported_for_platform(Platform.RETELL) is True
    assert runtime.supported_for_platform(Platform.VAPI) is False
    assert runtime.supported_for_platform(Platform.WEBHOOK) is False
    assert runtime.supported_for_platform(None) is False


def test_validate_config_requires_retell_agent() -> None:
    runtime = RetellRuntime()
    agent = _make_agent(Platform.VAPI)
    session = MagicMock()

    with pytest.raises(ValueError, match="Retell agent"):
        runtime.validate_config(RetellRuntimeConfig(), agent, session)


def test_validate_config_requires_integration_and_platform_agent_id() -> None:
    runtime = RetellRuntime()
    agent = _make_agent()
    agent.integration_id = None
    session = MagicMock()

    with pytest.raises(ValueError, match="integration"):
        runtime.validate_config(RetellRuntimeConfig(), agent, session)


async def test_test_connection_returns_not_implemented_for_valid_agent() -> None:
    runtime = RetellRuntime()
    agent = _make_agent()
    session = MagicMock()

    result = await runtime.test_connection(RetellRuntimeConfig(), agent, session)

    assert result.ok is False
    assert "not implemented" in result.message


async def test_run_test_case_is_explicitly_not_implemented() -> None:
    runtime = RetellRuntime()
    agent = _make_agent()
    test_case = MagicMock()
    args = RuntimeRunArgs(
        test_case=test_case,
        agent_snapshot=AgentSnapshot(
            agent=agent,
            agent_id=agent.id,
            platform=agent.platform,
            integration_id=agent.integration_id,
            platform_agent_id=agent.platform_agent_id,
            endpoint_url=None,
            system_prompt=None,
            tools=None,
            mode=AgentMode.PLATFORM,
            model=None,
            provider=None,
        ),
        run_snapshot=RunSnapshot(
            run_id=uuid.uuid4(),
            run_config=RunConfig(timeout_per_test_case_ms=100),
            cancel_event=None,
        ),
    )

    with pytest.raises(RetellRuntimeNotImplementedError, match="create-chat"):
        await runtime.run_test_case(RetellRuntimeConfig(), args, MagicMock())
