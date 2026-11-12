import httpx
import pytest
from connexity_mcp_server.client import ConnexityBackendClient, ConnexityBackendError
from connexity_mcp_server.config import Settings
from connexity_mcp_server.tools import (
    create_workspace,
    get_readiness,
    list_agents,
    list_workspaces,
)
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

WORKSPACE_ID = "3f1c9a52-0f5e-4a59-9a0c-2c3c1f0a7b10"
ANSWER = {
    "rules": ["A rule."],
    "next_steps": ["1. Do this."],
    "guide": "connexity://guides/workspaces",
}


def _authenticated():
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="user-oauth-token",
                client_id="claude-client",
                scopes=["mcp:access"],
            )
        )
    )


async def _call(handler, call):
    settings = Settings(connexity_api_url="http://backend:8000/api/v1")
    token = _authenticated()
    try:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            client = ConnexityBackendClient(settings=settings, http_client=http_client)
            return await call(client)
    finally:
        auth_context_var.reset(token)


@pytest.mark.asyncio
async def test_list_workspaces_forwards_the_token_and_keeps_the_answer() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/mcp/workspaces"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        return httpx.Response(
            200,
            json={
                "data": [{"id": WORKSPACE_ID, "name": "acme.com"}],
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(handler, lambda client: list_workspaces(client))

    assert [w.name for w in result.data] == ["acme.com"]
    assert result.rules == ["A rule."]
    assert result.next_steps == ["1. Do this."]
    assert result.guide == "connexity://guides/workspaces"


@pytest.mark.asyncio
async def test_list_agents_sends_workspace_query_cursor_and_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/agents"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        assert dict(request.url.params) == {
            "query": "booking",
            "cursor": "abc",
            "limit": "100",
        }
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "a1",
                        "name": "Car service booking",
                        "platform": "retell",
                        "platform_agent_name": None,
                        "created_at": "2026-11-12T10:00:00Z",
                    }
                ],
                "next_cursor": "next",
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: list_agents(
            client, workspace_id=WORKSPACE_ID, query="booking", cursor="abc", limit=500
        ),
    )

    assert [a.name for a in result.data] == ["Car service booking"]
    assert result.next_cursor == "next"


@pytest.mark.asyncio
async def test_an_error_in_the_standard_shape_reads_as_next_steps() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "detail": {
                    "error": "Workspace not found",
                    "next_steps": ["Call `list_workspaces`."],
                    "guide": "connexity://guides/workspaces",
                }
            },
        )

    with pytest.raises(ConnexityBackendError) as excinfo:
        await _call(handler, lambda client: list_agents(client, workspace_id="other"))

    assert str(excinfo.value) == (
        "Workspace not found. Next steps: 1. Call `list_workspaces`. "
        "Guide: connexity://guides/workspaces"
    )


@pytest.mark.asyncio
async def test_client_requires_authenticated_mcp_user() -> None:
    settings = Settings(connexity_api_url="http://backend:8000/api/v1")

    async with httpx.AsyncClient() as http_client:
        client = ConnexityBackendClient(settings=settings, http_client=http_client)
        with pytest.raises(ConnexityBackendError, match="authenticated MCP user"):
            await client.list_workspaces()


@pytest.mark.asyncio
async def test_an_invalid_argument_names_it_and_points_to_list_workspaces() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "detail": [
                    {
                        "loc": ["path", "workspace_id"],
                        "msg": "Input should be a valid UUID",
                        "type": "uuid_parsing",
                    }
                ]
            },
        )

    with pytest.raises(ConnexityBackendError) as excinfo:
        await _call(
            handler, lambda client: list_agents(client, workspace_id="acme.com")
        )

    message = str(excinfo.value)
    assert message.startswith(
        "Invalid arguments (`workspace_id`: Input should be a valid UUID)."
    )
    assert "list_workspaces" in message


@pytest.mark.asyncio
async def test_create_workspace_posts_the_name() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/mcp/workspaces"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        assert request.content == b'{"name":"Kestrel Plumbing"}'
        return httpx.Response(
            200,
            json={
                "data": {"id": WORKSPACE_ID, "name": "Kestrel Plumbing"},
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler, lambda client: create_workspace(client, name="Kestrel Plumbing")
    )

    assert result.data.name == "Kestrel Plumbing"


@pytest.mark.asyncio
async def test_get_readiness_reads_the_workspace_steps() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/readiness"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        return httpx.Response(
            200,
            json={
                "data": {
                    "steps": [
                        {
                            "key": "assistant",
                            "name": "Assistant connected",
                            "state": "done",
                            "detail": "Claude",
                        }
                    ],
                    "done": 1,
                    "total": 4,
                    "percent": 25,
                    "first_scan_done": False,
                    "connect_command": None,
                },
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler, lambda client: get_readiness(client, workspace_id=WORKSPACE_ID)
    )

    assert result.data.percent == 25
    assert result.data.steps[0].state == "done"
