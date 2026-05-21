from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MCP_CLIENT_ID = "mcp-server"


def _split_csv(value: str | None) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


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

    @property
    def normalized_api_url(self) -> str:
        value = self.connexity_api_url.strip().rstrip("/")
        if value.endswith("/api/v1"):
            return value
        return f"{value}/api/v1"

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
        origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
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

