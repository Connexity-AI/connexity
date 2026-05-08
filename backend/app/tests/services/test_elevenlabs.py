from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.elevenlabs import (
    check_elevenlabs_connection,
    deploy_elevenlabs_agent,
    list_elevenlabs_agents,
)


@pytest.mark.asyncio
async def test_test_elevenlabs_connection_uses_xi_api_key_header() -> None:
    response = httpx.Response(
        status_code=200,
        request=httpx.Request("GET", "https://api.elevenlabs.io/v1/user"),
    )
    with patch("app.services.elevenlabs.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = response
        mock_client_cls.return_value = mock_client

        ok = await check_elevenlabs_connection("eleven-key")

    assert ok is True
    headers = mock_client.get.call_args.kwargs["headers"]
    assert headers["xi-api-key"] == "eleven-key"


@pytest.mark.asyncio
async def test_list_elevenlabs_agents_maps_id_and_name() -> None:
    response = httpx.Response(
        status_code=200,
        json={"agents": [{"agent_id": "ag_1", "name": "Agent One"}]},
        request=httpx.Request("GET", "https://api.elevenlabs.io/v1/convai/agents"),
    )
    with patch("app.services.elevenlabs.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = response
        mock_client_cls.return_value = mock_client

        agents = await list_elevenlabs_agents("eleven-key")

    assert len(agents) == 1
    assert agents[0].agent_id == "ag_1"
    assert agents[0].agent_name == "Agent One"


@pytest.mark.asyncio
async def test_deploy_elevenlabs_agent_sends_prompt_model_and_temperature() -> None:
    response = httpx.Response(
        status_code=200,
        json={"version_id": "ver_123"},
        request=httpx.Request(
            "PATCH", "https://api.elevenlabs.io/v1/convai/agents/ag_1"
        ),
    )
    with patch("app.services.elevenlabs.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.patch.return_value = response
        mock_client_cls.return_value = mock_client

        result = await deploy_elevenlabs_agent(
            api_key="eleven-key",
            agent_id="ag_1",
            system_prompt="You are helpful.",
            agent_model="gpt-4o-mini",
            agent_temperature=0.2,
            tools=None,
            version_description="Connexity Agent v1",
        )

    assert result.success is True
    patched_json = mock_client.patch.call_args.kwargs["json"]
    prompt = (
        patched_json["conversation_config"]["agent"]["prompt"]["prompt"]
        if isinstance(patched_json, dict)
        else None
    )
    assert prompt == "You are helpful."
    assert (
        patched_json["conversation_config"]["agent"]["prompt"]["llm"] == "gpt-4o-mini"
    )
    assert patched_json["conversation_config"]["agent"]["prompt"]["temperature"] == 0.2
    assert patched_json["version_description"] == "Connexity Agent v1"
