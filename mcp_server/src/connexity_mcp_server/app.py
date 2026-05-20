from __future__ import annotations

import contextlib

from fastapi import FastAPI
from starlette.types import ASGIApp, Receive, Scope, Send
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from connexity_mcp_server.client import ConnexityBackendClient
from connexity_mcp_server.config import Settings
from connexity_mcp_server.models import (
    AgentDraftResult,
    FindAgentsResult,
    ListAgentsResult,
    UpdateAgentPromptResult,
)
from connexity_mcp_server.tools import (
    find_agents as _find_agents,
    get_agent_draft as _get_agent_draft,
    list_agents as _list_agents,
    update_agent_prompt as _update_agent_prompt,
)


class NormalizeMcpPathMiddleware:
    """Allow both `/mcp` and `/mcp/` to reach the mounted MCP app."""

    def __init__(self, app: ASGIApp, mcp_path: str) -> None:
        self.app = app
        self.mcp_path = mcp_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in {"http", "websocket"} and scope["path"] == self.mcp_path:
            scope = dict(scope)
            scope["path"] = f"{self.mcp_path}/"
            raw_path = scope.get("raw_path")
            if isinstance(raw_path, bytes):
                scope["raw_path"] = f"{self.mcp_path}/".encode("utf-8")
        await self.app(scope, receive, send)


def build_application(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    backend_client = ConnexityBackendClient(settings)
    mcp_server = FastMCP(
        settings.mcp_server_name,
        stateless_http=True,
        json_response=True,
        streamable_http_path="/",
        transport_security=TransportSecuritySettings(
            allowed_hosts=settings.resolved_allowed_hosts,
            allowed_origins=settings.resolved_allowed_origins,
        ),
    )

    @mcp_server.tool()
    async def list_agents(limit: int = 25) -> ListAgentsResult:
        return await _list_agents(client=backend_client, limit=limit)

    @mcp_server.tool()
    async def find_agents(query: str, limit: int = 10) -> FindAgentsResult:
        return await _find_agents(client=backend_client, query=query, limit=limit)

    @mcp_server.tool()
    async def get_agent_draft(agent_id: str) -> AgentDraftResult:
        return await _get_agent_draft(client=backend_client, agent_id=agent_id)

    @mcp_server.tool()
    async def update_agent_prompt(
        agent_id: str,
        system_prompt: str,
    ) -> UpdateAgentPromptResult:
        return await _update_agent_prompt(
            client=backend_client,
            agent_id=agent_id,
            system_prompt=system_prompt,
        )

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI):
        async with mcp_server.session_manager.run():
            try:
                yield
            finally:
                await backend_client.aclose()

    app = FastAPI(title="Connexity MCP Server", lifespan=lifespan)
    app.router.redirect_slashes = False

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    mcp_app = mcp_server.streamable_http_app()
    app.add_middleware(NormalizeMcpPathMiddleware, mcp_path=settings.normalized_mcp_path)
    app.mount(settings.normalized_mcp_path, mcp_app)
    app.mount(f"{settings.normalized_mcp_path}/", mcp_app)
    return app
