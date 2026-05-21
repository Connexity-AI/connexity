import json

import httpx
import pytest

from connexity_mcp_server.client import ConnexityBackendClient, ConnexityBackendError
from connexity_mcp_server.config import Settings


@pytest.mark.asyncio
async def test_client_exchanges_secret_for_service_jwt_once() -> None:
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path == "/api/v1/internal/token":
            payload = json.loads(request.content.decode("utf-8"))
            assert payload == {
                "client_id": "mcp-server",
                "client_secret": "very-long-random-string",
            }
            return httpx.Response(
                200,
                json={"access_token": "service-jwt", "expires_in": 300},
            )
        if request.url.path == "/api/v1/mcp/agents":
            assert request.headers["Authorization"] == "Bearer service-jwt"
            return httpx.Response(200, json={"data": [], "count": 0})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    settings = Settings(
        connexity_api_url="http://backend:8000/api/v1",
        mcp_client_secret="very-long-random-string",
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ConnexityBackendClient(settings=settings, http_client=http_client)
        first = await client.list_agents()
        second = await client.list_agents()

    assert first["count"] == 0
    assert second["count"] == 0
    assert requests.count(("POST", "/api/v1/internal/token")) == 1
    assert requests.count(("GET", "/api/v1/mcp/agents")) == 2


@pytest.mark.asyncio
async def test_client_uses_custom_client_id_override() -> None:
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path == "/api/v1/internal/token":
            payload = json.loads(request.content.decode("utf-8"))
            assert payload["client_id"] == "custom-mcp-client"
            return httpx.Response(
                200,
                json={"access_token": "service-jwt", "expires_in": 300},
            )
        if request.url.path == "/api/v1/mcp/agents":
            return httpx.Response(200, json={"data": [], "count": 0})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    settings = Settings(
        connexity_api_url="http://backend:8000/api/v1",
        mcp_client_id="custom-mcp-client",
        mcp_client_secret="very-long-random-string",
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ConnexityBackendClient(settings=settings, http_client=http_client)
        await client.list_agents()

    assert requests.count(("POST", "/api/v1/internal/token")) == 1


@pytest.mark.asyncio
async def test_client_requires_mcp_shared_secret_settings() -> None:
    settings = Settings(
        connexity_api_url="http://backend:8000/api/v1",
        mcp_client_secret="",
    )

    async with httpx.AsyncClient() as http_client:
        client = ConnexityBackendClient(settings=settings, http_client=http_client)
        with pytest.raises(ConnexityBackendError, match="MCP_CLIENT_SECRET"):
            await client.list_agents()
