"""CustomUrlEngine: connection probe + run-test-case dispatch."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent import Agent
from app.models.enums import AgentMode, Platform
from app.models.schemas import (
    ConnexityEngineConfig,
    CustomUrlEngineConfig,
    RunConfig,
)
from app.services.eval_engines.base import EngineRunArgs
from app.services.eval_engines.custom_url import CustomUrlEngine


def _make_agent(platform: Platform | None = Platform.WEBHOOK) -> Agent:
    return Agent(
        id=uuid.uuid4(),
        name="agent",
        mode=AgentMode.ENDPOINT,
        endpoint_url="http://localhost:8080/agent",
        platform=platform,
    )


def test_supported_for_platform() -> None:
    engine = CustomUrlEngine()
    assert engine.supported_for_platform(Platform.WEBHOOK) is True
    assert engine.supported_for_platform(None) is True
    assert engine.supported_for_platform(Platform.RETELL) is False
    assert engine.supported_for_platform(Platform.VAPI) is False


def test_validate_config_rejects_non_url_schemes() -> None:
    engine = CustomUrlEngine()
    agent = _make_agent()
    session = MagicMock()
    with pytest.raises(ValueError, match="http://"):
        engine.validate_config(
            CustomUrlEngineConfig(url="ftp://example.com"), agent, session
        )


def test_validate_config_accepts_https() -> None:
    engine = CustomUrlEngine()
    agent = _make_agent()
    session = MagicMock()
    engine.validate_config(
        CustomUrlEngineConfig(url="https://example.com/v1/chat/completions"),
        agent,
        session,
    )


def test_validate_config_rejects_wrong_kind() -> None:
    engine = CustomUrlEngine()
    agent = _make_agent()
    session = MagicMock()
    with pytest.raises(ValueError):
        engine.validate_config(ConnexityEngineConfig(), agent, session)


class _MockResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


async def test_test_connection_happy_path() -> None:
    engine = CustomUrlEngine()
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
        "app.services.eval_engines.custom_url.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await engine.test_connection(
            CustomUrlEngineConfig(url="https://example.com/v1"),
            agent,
            session,
        )

    assert result.ok is True


async def test_test_connection_http_error() -> None:
    engine = CustomUrlEngine()
    agent = _make_agent()
    session = MagicMock()

    mock_response = _MockResponse(500, {})

    with patch(
        "app.services.eval_engines.custom_url.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await engine.test_connection(
            CustomUrlEngineConfig(url="https://example.com/v1"),
            agent,
            session,
        )

    assert result.ok is False
    assert "500" in result.message


async def test_test_connection_malformed_response() -> None:
    engine = CustomUrlEngine()
    agent = _make_agent()
    session = MagicMock()

    mock_response = _MockResponse(200, {"messages": [{"role": "user", "content": "x"}]})

    with patch(
        "app.services.eval_engines.custom_url.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await engine.test_connection(
            CustomUrlEngineConfig(url="https://example.com/v1"),
            agent,
            session,
        )

    assert result.ok is False


async def test_run_test_case_overrides_endpoint_url() -> None:
    """The engine must pass cfg.url to the orchestrator instead of args.agent_endpoint_url."""
    engine = CustomUrlEngine()
    agent = _make_agent()
    session = MagicMock()

    test_case = MagicMock()
    args = EngineRunArgs(
        test_case=test_case,
        run_config=RunConfig(),
        agent=agent,
        agent_id=agent.id,
        agent_platform=agent.platform,
        agent_integration_id=agent.integration_id,
        agent_platform_agent_id=agent.platform_agent_id,
        agent_endpoint_url="http://stale-original/agent",
        agent_system_prompt=None,
        agent_tools=None,
        agent_mode=AgentMode.ENDPOINT,
        agent_model=None,
        agent_provider=None,
        cancel_event=None,
    )

    with patch(
        "app.services.orchestrator.run_test_case_with_evaluation",
        new_callable=AsyncMock,
    ) as mock_eval:
        mock_eval.return_value = (MagicMock(), MagicMock())
        await engine.run_test_case(
            CustomUrlEngineConfig(url="https://override/v1"),
            args,
            session,
        )

    assert mock_eval.await_count == 1
    forwarded_url = mock_eval.await_args.args[1]
    assert forwarded_url == "https://override/v1"
