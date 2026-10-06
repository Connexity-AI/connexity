from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.elevenlabs import (
    check_elevenlabs_connection,
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
