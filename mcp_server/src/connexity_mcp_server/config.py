from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


def _credentials_path() -> Path:
    xdg_config_home = Path.home() / ".config"
    base = Path.cwd()
    env_value = None
    try:
        from os import environ

        env_value = environ.get("XDG_CONFIG_HOME")
    except Exception:
        env_value = None
    if env_value:
        base = Path(env_value)
    else:
        base = xdg_config_home
    return base / "connexity-cli" / "credentials.json"


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
        extra="ignore",
    )

    connexity_api_url: str = Field(
        default="http://localhost:8000/api/v1",
        validation_alias=AliasChoices("CONNEXITY_API_URL", "API_URL"),
    )
    connexity_api_token: str | None = Field(default=None, alias="CONNEXITY_API_TOKEN")
    connexity_email: str | None = Field(default=None, alias="CONNEXITY_EMAIL")
    connexity_password: str | None = Field(default=None, alias="CONNEXITY_PASSWORD")
    dev_email: str | None = Field(default=None, alias="FIRST_SUPERUSER")
    dev_password: str | None = Field(default=None, alias="FIRST_SUPERUSER_PASSWORD")
    connexity_use_saved_cli_credentials: bool = Field(
        default=True,
        alias="CONNEXITY_USE_SAVED_CLI_CREDENTIALS",
    )
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
    def resolved_allowed_hosts(self) -> list[str]:
        hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
        for host in _split_csv(self.mcp_allowed_hosts):
            if host not in hosts:
                hosts.append(host)
        parsed_public_host = _extract_host(self.mcp_public_base_url)
        if parsed_public_host and parsed_public_host not in hosts:
            hosts.append(parsed_public_host)
        return hosts

    @property
    def resolved_allowed_origins(self) -> list[str]:
        origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
        for origin in _split_csv(self.mcp_allowed_origins):
            if origin not in origins:
                origins.append(origin)
        if isinstance(self.mcp_public_base_url, str) and self.mcp_public_base_url.strip():
            public_origin = self.mcp_public_base_url.strip().rstrip("/")
            if public_origin not in origins:
                origins.append(public_origin)
        return origins

    def load_saved_cli_token(self) -> str | None:
        if not self.connexity_use_saved_cli_credentials:
            return None

        path = _credentials_path()
        if not path.exists():
            return None

        try:
            raw = path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict):
            return None

        token = payload.get("token")
        if isinstance(token, str) and token.strip():
            return token.strip()
        return None
