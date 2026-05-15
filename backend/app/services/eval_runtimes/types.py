"""Shared runtime result + snapshot types."""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.models.agent import Agent
from app.models.enums import AgentMode, Platform
from app.models.schemas import ConversationTurn, RunConfig


@dataclass(frozen=True)
class AgentSnapshot:
    """Frozen capture of agent-related state at run-start time.

    The fields here come from the snapshotted ``agent_*`` columns on
    :class:`app.models.run.Run` plus the underlying :class:`Agent` row.
    ``mode`` reflects the effective :class:`~app.models.schemas.RunConfig`
    (simulator vs HTTP), not necessarily ``Run.agent_mode``.
    """

    agent: Agent
    agent_id: uuid.UUID
    platform: Platform | None
    integration_id: uuid.UUID | None
    platform_agent_id: str | None
    endpoint_url: str | None
    system_prompt: str | None
    tools: list[dict[str, Any]] | None
    mode: AgentMode
    model: str | None
    provider: str | None
    version: int | None = None


@dataclass(frozen=True)
class RunSnapshot:
    """Frozen capture of run-level state shared across every test case."""

    run_id: uuid.UUID
    run_config: RunConfig
    cancel_event: asyncio.Event | None


@dataclass(frozen=True)
class TestCaseRunResult:
    """Outcome of a test-case runtime execution before persistence.

    ``runtime_metadata`` is an opaque per-runtime escape hatch: voice runtimes
    use it to attach platform call ids, recording URLs, etc. Text runtimes
    typically leave it as ``None``.
    """

    transcript: list[ConversationTurn]
    agent_token_usage: dict[str, int | bool]
    platform_token_usage: dict[str, int]
    agent_cost_usd: float = 0.0
    platform_cost_usd: float = 0.0
    runtime_metadata: dict[str, Any] | None = field(default=None)
