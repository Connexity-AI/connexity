"""CustomEndpointRuntime: connection probe + run-test-case dispatch."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent import Agent
from app.models.enums import AgentMode, Platform
from app.models.schemas import (
    ConnexityRuntimeConfig,
    CustomEndpointRuntimeConfig,
    RunConfig,
)
from app.services.eval_runtimes import AgentSnapshot, RunSnapshot
from app.services.eval_runtimes.base import RuntimeRunArgs
from app.services.eval_runtimes.text.custom_endpoint import CustomEndpointRuntime


def _make_agent(platform: Platform | None = Platform.WEBHOOK) -> Agent:
    return Agent(
        id=uuid.uuid4(),
        name="agent",
        mode=AgentMode.ENDPOINT,
        endpoint_url="http://localhost:8080/agent",
        platform=platform,
    )


def test_supported_for_platform() -> None:
    runtime = CustomEndpointRuntime()
    assert runtime.supported_for_platform(Platform.WEBHOOK) is True
    assert runtime.supported_for_platform(None) is True
    assert runtime.supported_for_platform(Platform.RETELL) is False
    assert runtime.supported_for_platform(Platform.VAPI) is True


def test_validate_config_rejects_non_url_schemes() -> None:
    runtime = CustomEndpointRuntime()
    agent = _make_agent()
    session = MagicMock()
    with pytest.raises(ValueError, match="http://"):
        runtime.validate_config(
            CustomEndpointRuntimeConfig(url="ftp://example.com"), agent, session
        )


def test_validate_config_accepts_https() -> None:
    runtime = CustomEndpointRuntime()
    agent = _make_agent()
    session = MagicMock()
    runtime.validate_config(
        CustomEndpointRuntimeConfig(url="https://example.com/v1/chat/completions"),
        agent,
        session,
    )


def test_validate_config_rejects_wrong_kind() -> None:
    runtime = CustomEndpointRuntime()
    agent = _make_agent()
    session = MagicMock()
    with pytest.raises(ValueError):
        runtime.validate_config(ConnexityRuntimeConfig(), agent, session)


class _MockResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


async def test_test_connection_happy_path() -> None:
    runtime = CustomEndpointRuntime()
    agent = _make_agent()
    session = MagicMock()

    mock_response = _MockResponse(
        200,
        {
            "messages": [
                {"role": "assistant", "content": "hi"},
            ]
        },
    )

    with patch(
        "app.services.eval_runtimes.text.custom_endpoint.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await runtime.test_connection(
            CustomEndpointRuntimeConfig(url="https://example.com/v1"),
            agent,
            session,
        )

    assert result.ok is True


async def test_test_connection_http_error() -> None:
    runtime = CustomEndpointRuntime()
    agent = _make_agent()
    session = MagicMock()

    mock_response = _MockResponse(500, {})

    with patch(
        "app.services.eval_runtimes.text.custom_endpoint.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await runtime.test_connection(
            CustomEndpointRuntimeConfig(url="https://example.com/v1"),
            agent,
            session,
        )

    assert result.ok is False
    assert "500" in result.message


async def test_test_connection_malformed_response() -> None:
    runtime = CustomEndpointRuntime()
    agent = _make_agent()
    session = MagicMock()

    mock_response = _MockResponse(200, {"messages": [{"role": "user", "content": "x"}]})

    with patch(
        "app.services.eval_runtimes.text.custom_endpoint.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await runtime.test_connection(
            CustomEndpointRuntimeConfig(url="https://example.com/v1"),
            agent,
            session,
        )

    assert result.ok is False


async def test_run_test_case_overrides_endpoint_url() -> None:
    """The runtime must pass cfg.url to the text loop instead of agent.endpoint_url."""
    runtime = CustomEndpointRuntime()
    agent = _make_agent()
    session = MagicMock()

    test_case = MagicMock()
    test_case.id = uuid.uuid4()
    test_case.persona_context = None
    test_case.user_context = {}
    test_case.expected_outcomes = None
    test_case.first_message = "Hello"
    test_case.first_turn = None
    args = RuntimeRunArgs(
        test_case=test_case,
        agent_snapshot=AgentSnapshot(
            agent=agent,
            agent_id=agent.id,
            platform=agent.platform,
            integration_id=agent.integration_id,
            platform_agent_id=agent.platform_agent_id,
            endpoint_url="http://stale-original/agent",
            system_prompt=None,
            tools=None,
            mode=AgentMode.ENDPOINT,
            model=None,
            provider=None,
        ),
        run_snapshot=RunSnapshot(
            run_id=uuid.uuid4(),
            run_config=RunConfig(),
            cancel_event=None,
        ),
        test_case_result_id=uuid.uuid4(),
    )

    with patch.object(runtime, "do_agent_turn", new_callable=AsyncMock) as mock_turn:
        mock_turn.return_value = False
        await runtime.run_test_case(
            CustomEndpointRuntimeConfig(url="https://override/v1"),
            args,
            session,
        )

    assert mock_turn.await_count == 1
    forwarded_url = mock_turn.await_args.args[0].agent_config.endpoint_url
    assert forwarded_url == "https://override/v1"
