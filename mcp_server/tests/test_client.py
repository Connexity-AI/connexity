import httpx
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from connexity_mcp_server.client import ConnexityBackendClient, ConnexityBackendError
from connexity_mcp_server.config import Settings


@pytest.mark.asyncio
async def test_client_forwards_current_mcp_access_token() -> None:
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path == "/api/v1/mcp/agents":
            assert request.headers["Authorization"] == "Bearer user-oauth-token"
            return httpx.Response(200, json={"data": [], "count": 0})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    settings = Settings(connexity_api_url="http://backend:8000/api/v1")
    auth_token = auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="user-oauth-token",
                client_id="claude-client",
                scopes=["mcp:access"],
            )
        )
    )

    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = ConnexityBackendClient(settings=settings, http_client=http_client)
            result = await client.list_agents()
    finally:
        auth_context_var.reset(auth_token)

    assert result["count"] == 0
    assert requests == [("GET", "/api/v1/mcp/agents")]


@pytest.mark.asyncio
async def test_client_requires_authenticated_mcp_user() -> None:
    settings = Settings(connexity_api_url="http://backend:8000/api/v1")

    async with httpx.AsyncClient() as http_client:
        client = ConnexityBackendClient(settings=settings, http_client=http_client)
        with pytest.raises(ConnexityBackendError, match="authenticated MCP user"):
            await client.list_agents()
