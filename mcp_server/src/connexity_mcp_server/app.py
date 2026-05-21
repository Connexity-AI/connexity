from __future__ import annotations

import contextlib
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse, Response
import httpx
from mcp.server.auth.routes import build_resource_metadata_url
from starlette.types import ASGIApp, Receive, Scope, Send
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.server.streamable_http import MCP_PROTOCOL_VERSION_HEADER

from connexity_mcp_server.auth import OidcTokenVerifier
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
    settings.require_backend_service_auth()
    settings.require_mcp_oauth()
    backend_client = ConnexityBackendClient(settings)
    token_verifier = OidcTokenVerifier(settings)
    auth_settings = AuthSettings(
        issuer_url=settings.validated_mcp_oauth_issuer_url,
        resource_server_url=settings.validated_mcp_oauth_resource_server_url,
        required_scopes=settings.resolved_mcp_oauth_required_scopes or None,
    )
    mcp_server = FastMCP(
        settings.mcp_server_name,
        stateless_http=True,
        json_response=True,
        streamable_http_path="/",
        auth=auth_settings,
        token_verifier=token_verifier,
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
                await token_verifier.aclose()
                await backend_client.aclose()

    app = FastAPI(title="Connexity MCP Server", lifespan=lifespan)
    app.router.redirect_slashes = False

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    async def proxy_oauth_request(
        request: Request,
        backend_path: str,
    ) -> Response:
        cors_headers = _oauth_cors_headers(request=request, settings=settings)
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=cors_headers)

        upstream_url = f"{settings.normalized_backend_origin}{backend_path}"
        if request.url.query:
            upstream_url = f"{upstream_url}?{request.url.query}"

        body = await request.body()
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in {"host", "content-length"}
        }
        async with httpx.AsyncClient(
            timeout=settings.connexity_api_timeout_seconds,
            follow_redirects=False,
        ) as http_client:
            try:
                upstream_response = await http_client.request(
                    request.method,
                    upstream_url,
                    content=body,
                    headers=headers,
                )
            except httpx.HTTPError as exc:
                return JSONResponse(
                    {
                        "detail": (
                            "OAuth backend is not reachable from the MCP server. "
                            f"Expected backend origin: {settings.normalized_backend_origin}"
                        ),
                        "error": str(exc),
                    },
                    status_code=502,
                )

        response_headers = {
            key: value
            for key, value in upstream_response.headers.items()
            if key.lower()
            not in {
                "content-encoding",
                "content-length",
                "connection",
                "transfer-encoding",
            }
        }
        location = response_headers.get("location")
        if location:
            response_headers["location"] = _rewrite_backend_location(
                location=location,
                settings=settings,
            )
        response_headers.update(cors_headers)
        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=response_headers,
            media_type=upstream_response.headers.get("content-type"),
        )

    @app.api_route(
        "/.well-known/oauth-authorization-server",
        methods=["GET", "OPTIONS"],
    )
    async def oauth_authorization_server_metadata_proxy(request: Request) -> Response:
        return await proxy_oauth_request(
            request,
            "/.well-known/oauth-authorization-server",
        )

    @app.api_route(
        "/.well-known/openid-configuration",
        methods=["GET", "OPTIONS"],
    )
    async def openid_configuration_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/.well-known/openid-configuration")

    @app.api_route("/.well-known/jwks.json", methods=["GET", "OPTIONS"])
    async def jwks_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/.well-known/jwks.json")

    @app.api_route("/oauth/register", methods=["POST", "OPTIONS"])
    async def oauth_register_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/register")

    @app.api_route("/register", methods=["POST", "OPTIONS"])
    async def oauth_register_root_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/register")

    @app.api_route("/oauth/authorize", methods=["GET", "POST", "OPTIONS"])
    async def oauth_authorize_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize")

    @app.api_route("/authorize", methods=["GET", "POST", "OPTIONS"])
    async def oauth_authorize_root_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize")

    @app.api_route(
        "/oauth/authorize/confirm",
        methods=["POST", "OPTIONS"],
    )
    async def oauth_authorize_confirm_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize/confirm")

    @app.api_route(
        "/oauth/authorize/signup",
        methods=["GET", "OPTIONS"],
    )
    async def oauth_authorize_signup_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize/signup")

    @app.api_route(
        "/oauth/authorize/signup/confirm",
        methods=["POST", "OPTIONS"],
    )
    async def oauth_authorize_signup_confirm_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize/signup/confirm")

    @app.api_route("/token", methods=["POST", "OPTIONS"])
    async def oauth_token_root_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/token")

    @app.api_route("/oauth/token", methods=["POST", "OPTIONS"])
    async def oauth_token_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/token")

    protected_resource_metadata_url = build_resource_metadata_url(
        settings.validated_mcp_oauth_resource_server_url
    )
    protected_resource_metadata_path = urlparse(str(protected_resource_metadata_url)).path
    protected_resource_metadata = {
        "resource": settings.resolved_mcp_oauth_resource_server_url,
        "authorization_servers": [settings.resolved_mcp_oauth_issuer_url],
        "scopes_supported": settings.resolved_mcp_oauth_required_scopes or None,
        "resource_name": settings.mcp_server_name,
    }
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": MCP_PROTOCOL_VERSION_HEADER,
    }

    @app.options(protected_resource_metadata_path)
    async def oauth_protected_resource_metadata_options() -> Response:
        return Response(status_code=204, headers=cors_headers)

    @app.get(protected_resource_metadata_path)
    async def oauth_protected_resource_metadata() -> JSONResponse:
        return JSONResponse(protected_resource_metadata, headers=cors_headers)

    if settings.normalized_mcp_path != "/":
        # Some hosted MCP clients probe the bare origin even when the
        # canonical transport is mounted at a subpath like `/mcp`.
        @app.options("/.well-known/oauth-protected-resource")
        async def oauth_protected_resource_metadata_root_options() -> Response:
            return Response(status_code=204, headers=cors_headers)

        @app.get("/.well-known/oauth-protected-resource")
        async def oauth_protected_resource_metadata_root() -> JSONResponse:
            return JSONResponse(protected_resource_metadata, headers=cors_headers)

    mcp_app = mcp_server.streamable_http_app()
    app.add_middleware(NormalizeMcpPathMiddleware, mcp_path=settings.normalized_mcp_path)
    app.mount(settings.normalized_mcp_path, mcp_app)
    app.mount(f"{settings.normalized_mcp_path}/", mcp_app)
    if settings.normalized_mcp_path != "/":
        app.mount("/", mcp_app)
    return app


def _rewrite_backend_location(*, location: str, settings: Settings) -> str:
    public_base_url = settings.resolved_mcp_public_base_url
    if not public_base_url:
        return location

    backend_origin = settings.normalized_backend_origin
    if location.startswith(backend_origin):
        return f"{public_base_url}{location[len(backend_origin):]}"
    return location


def _oauth_cors_headers(*, request: Request, settings: Settings) -> dict[str, str]:
    origin = request.headers.get("origin")
    if not origin or not _origin_is_allowed(
        origin=origin,
        allowed_origins=settings.resolved_allowed_origins,
    ):
        return {}

    requested_headers = request.headers.get("access-control-request-headers")
    allow_headers = requested_headers or "Authorization, Content-Type, Accept"
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": allow_headers,
        "Vary": "Origin",
    }


def _origin_is_allowed(*, origin: str, allowed_origins: list[str]) -> bool:
    origin_parts = urlparse(origin)
    for allowed_origin in allowed_origins:
        if origin == allowed_origin:
            return True

        if not allowed_origin.endswith(":*"):
            continue

        allowed_base = allowed_origin[:-2]
        allowed_parts = urlparse(allowed_base)
        if (
            allowed_parts.scheme == origin_parts.scheme
            and allowed_parts.hostname == origin_parts.hostname
            and origin_parts.port is not None
        ):
            return True

    return False
