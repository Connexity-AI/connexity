"""Retell runtime behavior."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent import Agent
from app.models.enums import AgentMode, FirstTurn, Platform
from app.models.schemas import RetellRuntimeConfig, RunConfig
from app.services.eval_runtimes import AgentSnapshot, RunSnapshot
from app.services.eval_runtimes.base import RuntimeRunArgs
from app.services.eval_runtimes.text.retell import RetellRuntime
from app.services.retell import (
    RetellAgentPlaygroundCompletionResult,
    RetellChatMessage,
)


def _make_agent(platform: Platform | None = Platform.RETELL) -> Agent:
    return Agent(
        id=uuid.uuid4(),
        name="agent",
        mode=AgentMode.PLATFORM,
        endpoint_url=None,
        platform=platform,
        integration_id=uuid.uuid4(),
        platform_agent_id="retell_chat_agent_123",
    )


def _make_test_case(
    *,
    first_message: str = "Hello there",
    first_turn: FirstTurn = FirstTurn.USER,
):
    return SimpleNamespace(
        id=uuid.uuid4(),
        persona_context=None,
        user_context={},
        expected_outcomes=None,
        first_message=first_message,
        first_turn=first_turn,
    )


def _make_args(agent: Agent, test_case, *, max_turns: int | None = 1) -> RuntimeRunArgs:
    return RuntimeRunArgs(
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
            version=7,
        ),
        run_snapshot=RunSnapshot(
            run_id=uuid.uuid4(),
            run_config=RunConfig(max_turns=max_turns),
            cancel_event=None,
        ),
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


async def test_test_connection_checks_retell_playground() -> None:
    runtime = RetellRuntime()
    agent = _make_agent()
    session = MagicMock()
    session.get.return_value = SimpleNamespace(encrypted_api_key="ciphertext")

    with (
        patch(
            "app.services.eval_runtimes.text.retell.decrypt", return_value="retell-key"
        ),
        patch(
            "app.services.eval_runtimes.text.retell.create_retell_agent_playground_completion",
            new=AsyncMock(
                return_value=RetellAgentPlaygroundCompletionResult(success=True)
            ),
        ) as mock_playground,
    ):
        result = await runtime.test_connection(RetellRuntimeConfig(), agent, session)

    assert result.ok is True
    assert "reachable" in result.message
    mock_playground.assert_awaited_once_with(
        api_key="retell-key",
        retell_agent_id="retell_chat_agent_123",
        messages=[],
    )


async def test_test_connection_surfaces_playground_error() -> None:
    runtime = RetellRuntime()
    agent = _make_agent()
    session = MagicMock()
    session.get.return_value = SimpleNamespace(encrypted_api_key="ciphertext")

    with (
        patch(
            "app.services.eval_runtimes.text.retell.decrypt", return_value="retell-key"
        ),
        patch(
            "app.services.eval_runtimes.text.retell.create_retell_agent_playground_completion",
            new=AsyncMock(
                return_value=RetellAgentPlaygroundCompletionResult(
                    success=False,
                    error_message="Playground rejected the request",
                )
            ),
        ),
    ):
        result = await runtime.test_connection(RetellRuntimeConfig(), agent, session)

    assert result.ok is False
    assert result.message == "Playground rejected the request"


async def test_run_test_case_uses_retell_playground() -> None:
    runtime = RetellRuntime()
    agent = _make_agent()
    test_case = _make_test_case()
    args = _make_args(agent, test_case, max_turns=1)
    session = MagicMock()
    session.get.return_value = SimpleNamespace(encrypted_api_key="ciphertext")

    with (
        patch(
            "app.services.eval_runtimes.text.retell.decrypt", return_value="retell-key"
        ),
        patch(
            "app.services.eval_runtimes.text.retell.create_retell_agent_playground_completion",
            new=AsyncMock(
                side_effect=[
                    RetellAgentPlaygroundCompletionResult(success=True),
                    RetellAgentPlaygroundCompletionResult(
                        success=True,
                        current_state="collect_issue",
                        dynamic_variables={"customer_tier": "gold"},
                        call_ended=False,
                        messages=[
                            RetellChatMessage(
                                role="agent", content="Hi, how can I help?"
                            )
                        ],
                        latency_ms=321,
                    ),
                ]
            ),
        ) as mock_playground,
    ):
        result = await runtime.run_test_case(RetellRuntimeConfig(), args, session)

    assert [turn.role.value for turn in result.transcript] == ["user", "assistant"]
    assert result.transcript[0].content == "Hello there"
    assert result.transcript[1].content == "Hi, how can I help?"
    assert result.transcript[1].latency_ms == 321
    assert len(mock_playground.await_args_list) == 2
    assert mock_playground.await_args_list[0].kwargs == {
        "api_key": "retell-key",
        "retell_agent_id": "retell_chat_agent_123",
        "messages": [],
        "dynamic_variables": None,
    }
    assert mock_playground.await_args_list[1].kwargs == {
        "api_key": "retell-key",
        "retell_agent_id": "retell_chat_agent_123",
        "messages": [{"role": "user", "content": "Hello there"}],
        "dynamic_variables": None,
        "current_state": None,
        "current_node_id": None,
        "component_id": None,
    }


async def test_run_test_case_preserves_retell_opening_message() -> None:
    runtime = RetellRuntime()
    agent = _make_agent()
    test_case = _make_test_case(first_message="I need help", first_turn=FirstTurn.USER)
    args = _make_args(agent, test_case, max_turns=0)
    session = MagicMock()
    session.get.return_value = SimpleNamespace(encrypted_api_key="ciphertext")

    with (
        patch(
            "app.services.eval_runtimes.text.retell.decrypt", return_value="retell-key"
        ),
        patch(
            "app.services.eval_runtimes.text.retell.create_retell_agent_playground_completion",
            new=AsyncMock(
                return_value=RetellAgentPlaygroundCompletionResult(
                    success=True,
                    messages=[
                        RetellChatMessage(role="agent", content="Hi, how can I help?")
                    ],
                    latency_ms=111,
                )
            ),
        ),
    ):
        result = await runtime.run_test_case(RetellRuntimeConfig(), args, session)

    assert [turn.role.value for turn in result.transcript] == ["assistant", "user"]
    assert result.transcript[0].content == "Hi, how can I help?"
    assert result.transcript[0].latency_ms == 111
    assert result.transcript[1].content == "I need help"


async def test_run_test_case_carries_playground_state_between_turns() -> None:
    runtime = RetellRuntime()
    agent = _make_agent()
    test_case = _make_test_case()
    args = _make_args(agent, test_case, max_turns=1)
    session = MagicMock()
    session.get.return_value = SimpleNamespace(encrypted_api_key="ciphertext")

    with (
        patch(
            "app.services.eval_runtimes.text.retell.decrypt", return_value="retell-key"
        ),
        patch(
            "app.services.eval_runtimes.text.retell.create_retell_agent_playground_completion",
            new=AsyncMock(
                side_effect=[
                    RetellAgentPlaygroundCompletionResult(
                        success=True,
                        current_state="collect_issue",
                        current_node_id="node_start",
                        dynamic_variables={"customer_name": "Avery"},
                    ),
                    RetellAgentPlaygroundCompletionResult(
                        success=True,
                        messages=[
                            RetellChatMessage(
                                role="agent", content="How is the PTO being operated?"
                            )
                        ],
                        current_state="collect_issue",
                        current_node_id="node_followup",
                        dynamic_variables={"customer_name": "Avery"},
                    ),
                ]
            ),
        ) as mock_playground,
    ):
        result = await runtime.run_test_case(RetellRuntimeConfig(), args, session)

    assert [turn.role.value for turn in result.transcript] == ["user", "assistant"]
    assert result.transcript[1].content == "How is the PTO being operated?"
    assert len(mock_playground.await_args_list) == 2
    assert mock_playground.await_args_list[1].kwargs == {
        "api_key": "retell-key",
        "retell_agent_id": "retell_chat_agent_123",
        "messages": [{"role": "user", "content": "Hello there"}],
        "dynamic_variables": {"customer_name": "Avery"},
        "current_state": "collect_issue",
        "current_node_id": "node_start",
        "component_id": None,
    }
