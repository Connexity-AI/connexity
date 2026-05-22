from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from pydantic import AliasChoices, AnyHttpUrl, Field, TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MCP_CLIENT_ID = "mcp-server"
DEFAULT_MCP_OAUTH_REQUIRED_SCOPES = "mcp:access"
HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)
DEFAULT_BROWSER_ALLOWED_ORIGINS = (
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
    "https://claude.ai",
    "https://claude.com",
)


def _split_csv(value: str | None) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _split_scopes(value: str | None) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []

    normalized = value.replace(",", " ")
    return [item.strip() for item in normalized.split() if item.strip()]


def _extract_host(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = urlparse(value.strip())
    return parsed.netloc or None


class Settings(BaseSettings):
    """Runtime configuration for the standalone MCP service."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_prefix="",
        env_ignore_empty=True,
        extra="ignore",
        populate_by_name=True,
    )

    connexity_api_url: str = Field(
        default="http://localhost:8000/api/v1",
        validation_alias=AliasChoices("CONNEXITY_API_URL", "API_URL"),
    )
    mcp_client_id: str = Field(default=DEFAULT_MCP_CLIENT_ID, alias="MCP_CLIENT_ID")
    mcp_client_secret: str | None = Field(default=None, alias="MCP_CLIENT_SECRET")
    connexity_api_timeout_seconds: float = Field(
        default=15.0,
        alias="CONNEXITY_API_TIMEOUT_SECONDS",
    )

    mcp_host: str = Field(default="0.0.0.0", alias="MCP_HOST")
    mcp_port: int = Field(default=8001, alias="MCP_PORT")
    mcp_path: str = Field(default="/mcp", alias="MCP_PATH")
    mcp_server_name: str = Field(default="connexity-mcp", alias="MCP_SERVER_NAME")
    mcp_public_base_url: str | None = Field(default=None, alias="MCP_PUBLIC_BASE_URL")
    mcp_allowed_hosts: str | None = Field(default=None, alias="MCP_ALLOWED_HOSTS")
    mcp_allowed_origins: str | None = Field(default=None, alias="MCP_ALLOWED_ORIGINS")
    mcp_oauth_issuer_url: str | None = Field(default=None, alias="MCP_OAUTH_ISSUER_URL")
    mcp_oauth_audience: str | None = Field(default=None, alias="MCP_OAUTH_AUDIENCE")
    mcp_oauth_discovery_url: str | None = Field(default=None, alias="MCP_OAUTH_DISCOVERY_URL")
    mcp_oauth_jwks_url: str | None = Field(default=None, alias="MCP_OAUTH_JWKS_URL")
    mcp_oauth_required_scopes: str | None = Field(
        default=DEFAULT_MCP_OAUTH_REQUIRED_SCOPES,
        alias="MCP_OAUTH_REQUIRED_SCOPES",
    )
    mcp_oauth_resource_server_url: str | None = Field(default=None, alias="MCP_OAUTH_RESOURCE_SERVER_URL")

    @property
    def normalized_api_url(self) -> str:
        value = self.connexity_api_url.strip().rstrip("/")
        if value.endswith("/api/v1"):
            return value
        return f"{value}/api/v1"

    @property
    def normalized_backend_origin(self) -> str:
        api_url = self.normalized_api_url
        if api_url.endswith("/api/v1"):
            return api_url[: -len("/api/v1")]
        return api_url.rstrip("/")

    @property
    def normalized_mcp_path(self) -> str:
        path = self.mcp_path.strip() or "/mcp"
        if not path.startswith("/"):
            path = f"/{path}"
        return path.rstrip("/") or "/"

    @property
    def resolved_mcp_public_base_url(self) -> str | None:
        if isinstance(self.mcp_public_base_url, str) and self.mcp_public_base_url.strip():
            return self.mcp_public_base_url.strip().rstrip("/")

        railway_public_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        if isinstance(railway_public_domain, str) and railway_public_domain.strip():
            return f"https://{railway_public_domain.strip().rstrip('/')}"

        return None

    @property
    def resolved_allowed_hosts(self) -> list[str]:
        hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
        for host in _split_csv(self.mcp_allowed_hosts):
            if host not in hosts:
                hosts.append(host)
        parsed_public_host = _extract_host(self.resolved_mcp_public_base_url)
        if parsed_public_host and parsed_public_host not in hosts:
            hosts.append(parsed_public_host)
        return hosts

    @property
    def resolved_allowed_origins(self) -> list[str]:
        origins = list(DEFAULT_BROWSER_ALLOWED_ORIGINS)
        for origin in _split_csv(self.mcp_allowed_origins):
            if origin not in origins:
                origins.append(origin)
        public_origin = self.resolved_mcp_public_base_url
        if public_origin:
            if public_origin not in origins:
                origins.append(public_origin)
        return origins

    @property
    def resolved_mcp_client_id(self) -> str:
        if self.mcp_client_id.strip():
            return self.mcp_client_id.strip()
        return DEFAULT_MCP_CLIENT_ID

    @property
    def oauth_enabled(self) -> bool:
        return bool(self.resolved_mcp_oauth_issuer_url and self.resolved_mcp_oauth_resource_server_url)

    def require_mcp_oauth(self) -> None:
        missing: list[str] = []
        if self.resolved_mcp_oauth_issuer_url is None:
            missing.append("MCP_OAUTH_ISSUER_URL")
        if self.resolved_mcp_oauth_resource_server_url is None:
            missing.append("MCP_PUBLIC_BASE_URL or MCP_OAUTH_RESOURCE_SERVER_URL")

        if missing:
            missing_vars = ", ".join(missing)
            raise ValueError(
                "MCP transport auth is mandatory. "
                f"Missing required configuration: {missing_vars}."
            )

        # Validate URL formats eagerly so startup fails before the server binds.
        _ = self.validated_mcp_oauth_issuer_url
        _ = self.validated_mcp_oauth_resource_server_url

    def require_backend_service_auth(self) -> None:
        client_secret = (
            self.mcp_client_secret.strip()
            if isinstance(self.mcp_client_secret, str)
            else ""
        )
        if not client_secret:
            raise ValueError(
                "Connexity backend service auth is mandatory. Missing required "
                "configuration: MCP_CLIENT_SECRET."
            )

    @property
    def resolved_mcp_oauth_issuer_url(self) -> str | None:
        if isinstance(self.mcp_oauth_issuer_url, str) and self.mcp_oauth_issuer_url.strip():
            return self.mcp_oauth_issuer_url.strip().rstrip("/")
        return None

    @property
    def resolved_mcp_oauth_resource_server_url(self) -> str | None:
        if isinstance(self.mcp_oauth_resource_server_url, str) and self.mcp_oauth_resource_server_url.strip():
            return self.mcp_oauth_resource_server_url.strip().rstrip("/")

        public_base_url = self.resolved_mcp_public_base_url
        if public_base_url:
            return f"{public_base_url}{self.normalized_mcp_path}".rstrip("/")

        return None

    @property
    def resolved_mcp_oauth_audience(self) -> str | None:
        if isinstance(self.mcp_oauth_audience, str) and self.mcp_oauth_audience.strip():
            return self.mcp_oauth_audience.strip()
        return self.resolved_mcp_oauth_resource_server_url

    @property
    def resolved_mcp_oauth_discovery_url(self) -> str | None:
        if isinstance(self.mcp_oauth_discovery_url, str) and self.mcp_oauth_discovery_url.strip():
            return self.mcp_oauth_discovery_url.strip()

        issuer_url = self.resolved_mcp_oauth_issuer_url
        if issuer_url:
            return f"{issuer_url}/.well-known/openid-configuration"

        return None

    @property
    def resolved_mcp_oauth_jwks_url(self) -> str | None:
        if isinstance(self.mcp_oauth_jwks_url, str) and self.mcp_oauth_jwks_url.strip():
            return self.mcp_oauth_jwks_url.strip()
        return None

    @property
    def resolved_mcp_oauth_required_scopes(self) -> list[str]:
        return _split_scopes(self.mcp_oauth_required_scopes)

    @property
    def validated_mcp_oauth_issuer_url(self) -> AnyHttpUrl:
        issuer_url = self.resolved_mcp_oauth_issuer_url
        if issuer_url is None:
            raise ValueError("MCP OAuth issuer URL is not configured.")
        return HTTP_URL_ADAPTER.validate_python(issuer_url)

    @property
    def validated_mcp_oauth_resource_server_url(self) -> AnyHttpUrl:
        resource_server_url = self.resolved_mcp_oauth_resource_server_url
        if resource_server_url is None:
            raise ValueError("MCP OAuth resource server URL is not configured.")
        return HTTP_URL_ADAPTER.validate_python(resource_server_url)

