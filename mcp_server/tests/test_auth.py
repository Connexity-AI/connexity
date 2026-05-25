import json

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from connexity_mcp_server import app as app_module
from connexity_mcp_server.app import build_application
from connexity_mcp_server.auth import OidcTokenVerifier
from connexity_mcp_server.config import Settings


def test_build_application_requires_mcp_oauth_configuration() -> None:
    settings = Settings(mcp_public_base_url=None, mcp_oauth_issuer_url=None)

    with pytest.raises(
        ValueError,
        match="MCP transport auth is mandatory",
    ):
        build_application(settings)


def test_build_application_does_not_require_backend_client_secret() -> None:
    settings = Settings(
        mcp_public_base_url="https://mcp.example.com",
        mcp_oauth_issuer_url="https://tenant.example.com",
    )

    app = build_application(settings)

    assert app.title == "Connexity MCP Server"


def test_streamable_http_requires_bearer_token_and_exposes_protected_resource_metadata() -> None:
    settings = Settings(
        mcp_public_base_url="https://mcp.example.com",
        mcp_oauth_issuer_url="https://tenant.example.com",
    )

    app = build_application(settings)

    with TestClient(app) as client:
        response = client.get("/mcp")
        assert response.status_code == 401
        assert (
            response.headers["www-authenticate"]
            == 'Bearer error="invalid_token", error_description="Authentication required", '
            'resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource/mcp"'
        )

        metadata = client.get("/.well-known/oauth-protected-resource/mcp")
        assert metadata.status_code == 200
        assert metadata.headers["access-control-allow-origin"] == "*"
        assert metadata.json() == {
            "resource": "https://mcp.example.com/mcp",
            "authorization_servers": ["https://tenant.example.com"],
            "scopes_supported": ["mcp:access"],
            "resource_name": "connexity-mcp",
        }


def test_root_alias_supports_bare_origin_clients() -> None:
    settings = Settings(
        mcp_public_base_url="https://mcp.example.com",
        mcp_oauth_issuer_url="https://tenant.example.com",
    )

    app = build_application(settings)

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 401
        assert (
            response.headers["www-authenticate"]
            == 'Bearer error="invalid_token", error_description="Authentication required", '
            'resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource/mcp"'
        )

        metadata = client.get("/.well-known/oauth-protected-resource")
        assert metadata.status_code == 200
        assert metadata.headers["access-control-allow-origin"] == "*"
        assert metadata.json() == {
            "resource": "https://mcp.example.com/mcp",
            "authorization_servers": ["https://tenant.example.com"],
            "scopes_supported": ["mcp:access"],
            "resource_name": "connexity-mcp",
        }


def test_settings_allow_claude_origins_by_default() -> None:
    settings = Settings(
        mcp_public_base_url="https://mcp.example.com",
        mcp_oauth_issuer_url="https://tenant.example.com",
    )

    assert "https://claude.ai" in settings.resolved_allowed_origins
    assert "https://claude.com" in settings.resolved_allowed_origins


def test_oauth_proxy_adds_cors_headers_for_claude_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        connexity_api_url="https://backend.example.com/api/v1",
        mcp_public_base_url="https://mcp.example.com",
        mcp_oauth_issuer_url="https://tenant.example.com",
    )

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def aclose(self) -> None:
            return None

        async def request(self, method: str, url: str, content: bytes, headers: dict[str, str]) -> httpx.Response:
            assert method == "GET"
            assert url == "https://backend.example.com/.well-known/openid-configuration"
            assert headers["origin"] == "https://claude.ai"
            return httpx.Response(
                200,
                json={"issuer": "https://tenant.example.com"},
                headers={"content-type": "application/json"},
            )

    monkeypatch.setattr(app_module.httpx, "AsyncClient", FakeAsyncClient)
    app = build_application(settings)

    with TestClient(app) as client:
        response = client.get(
            "/.well-known/openid-configuration",
            headers={"Origin": "https://claude.ai"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://claude.ai"
    assert response.headers["vary"] == "Origin"
    assert response.json() == {"issuer": "https://tenant.example.com"}


@pytest.mark.asyncio
async def test_oidc_token_verifier_accepts_valid_jwt_access_tokens() -> None:
    issuer = "https://tenant.example.com"
    audience = "https://mcp.example.com/mcp"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    public_jwk["kid"] = "test-key"
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx.Response(200, json={"jwks_uri": f"{issuer}/.well-known/jwks.json"})
        if request.url.path == "/.well-known/jwks.json":
            return httpx.Response(200, json={"keys": [public_jwk]})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    token = jwt.encode(
        {
            "sub": "user_123",
            "azp": "claude-ai",
            "iss": issuer,
            "aud": audience,
            "exp": 4_102_444_800,
            "scope": "mcp:access",
        },
        private_key_pem,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    settings = Settings(
        mcp_public_base_url="https://mcp.example.com",
        mcp_oauth_issuer_url=issuer,
        mcp_oauth_audience=audience,
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        verifier = OidcTokenVerifier(settings=settings, http_client=http_client)
        access_token = await verifier.verify_token(token)

    assert access_token is not None
    assert access_token.client_id == "claude-ai"
    assert access_token.scopes == ["mcp:access"]
    assert access_token.resource == audience


@pytest.mark.asyncio
async def test_oidc_token_verifier_rejects_wrong_audience() -> None:
    issuer = "https://tenant.example.com"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    public_jwk["kid"] = "test-key"
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx.Response(200, json={"jwks_uri": f"{issuer}/.well-known/jwks.json"})
        if request.url.path == "/.well-known/jwks.json":
            return httpx.Response(200, json={"keys": [public_jwk]})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    token = jwt.encode(
        {
            "sub": "user_123",
            "iss": issuer,
            "aud": "https://another-resource.example.com/mcp",
            "exp": 4_102_444_800,
            "scope": "mcp:access",
        },
        private_key_pem,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    settings = Settings(
        mcp_public_base_url="https://mcp.example.com",
        mcp_oauth_issuer_url=issuer,
        mcp_oauth_audience="https://mcp.example.com/mcp",
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        verifier = OidcTokenVerifier(settings=settings, http_client=http_client)
        access_token = await verifier.verify_token(token)

    assert access_token is None
