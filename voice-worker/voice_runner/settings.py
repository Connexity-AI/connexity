"""Voice worker-specific settings layered on Connexity backend defaults."""

from __future__ import annotations

import os
import socket

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Env for the standalone worker process (reads repo-root `.env` like the backend)."""

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # HTTP server for Twilio (TwiML + media WebSocket).
    VOICE_WORKER_HTTP_HOST: str = "0.0.0.0"
    VOICE_WORKER_HTTP_PORT: int = Field(default=8765, ge=1, le=65535)

    # Public origin Twilio reaches (HTTPS). Used for REST dial webhook + WSS.
    VOICE_PUBLIC_BASE_URL: str | None = Field(
        default=None,
        description="Public https://… origin (no path, no trailing slash).",
    )

    # Kubernetes multi-replica: https://{POD_NAME}.{suffix}
    VOICE_WORKER_PUBLIC_HOST_SUFFIX: str | None = Field(
        default=None,
        description=(
            "DNS suffix for per-pod worker URLs in Kubernetes "
            "(combined with POD_NAME when VOICE_PUBLIC_BASE_URL is unset)."
        ),
    )

    # Job lease & polling.
    VOICE_JOB_LEASE_FLOOR_SECONDS: int = Field(
        default=600,
        ge=60,
        description="Minimum Postgres lease TTL for claimed jobs.",
    )
    VOICE_JOB_LEASE_BUFFER_SECONDS: int = Field(
        default=120,
        ge=0,
        description="Added to job max_call_duration when computing lease TTL.",
    )
    VOICE_WORKER_POLL_IDLE_SECONDS: float = Field(default=2.0, gt=0)
    VOICE_WORKER_CONNECT_TIMEOUT_SECONDS: float = Field(
        default=120.0,
        gt=5,
        description="Max seconds to wait for Twilio Media Stream start after dialing.",
    )
    VOICE_WORKER_LEASE_RENEW_SECONDS: float = Field(
        default=30.0,
        gt=5,
        description="Heartbeat interval while a call runs to extend job lease.",
    )

    WORKER_INSTANCE_ID: str | None = Field(
        default=None,
        description="Override worker identifier stored on claimed jobs.",
    )


def pod_name_from_env() -> str | None:
    raw = (os.environ.get("POD_NAME") or "").strip()
    return raw or None


def computed_worker_id(base: WorkerSettings) -> str:
    if base.WORKER_INSTANCE_ID:
        return base.WORKER_INSTANCE_ID.strip()
    pod = pod_name_from_env()
    if pod:
        return pod
    return f"{socket.gethostname()}-{id(base)}"


def resolved_public_base_url(settings: WorkerSettings) -> str:
    explicit = (settings.VOICE_PUBLIC_BASE_URL or "").strip().rstrip("/")
    if explicit:
        return explicit

    suffix = (settings.VOICE_WORKER_PUBLIC_HOST_SUFFIX or "").strip().lstrip(".")
    pod = pod_name_from_env()
    if suffix and pod:
        return f"https://{pod}.{suffix}"

    msg = (
        "Configure VOICE_PUBLIC_BASE_URL (local/single-replica) or "
        "VOICE_WORKER_PUBLIC_HOST_SUFFIX with POD_NAME (Kubernetes multi-replica)."
    )
    raise ValueError(msg)


def lease_ttl_seconds(
    *, max_call_duration_seconds: int, settings: WorkerSettings
) -> int:
    dynamic = max_call_duration_seconds + settings.VOICE_JOB_LEASE_BUFFER_SECONDS
    return max(settings.VOICE_JOB_LEASE_FLOOR_SECONDS, dynamic)
