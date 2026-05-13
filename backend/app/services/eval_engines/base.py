"""Evaluation engine abstraction.

An evaluation engine is the strategy that drives a single test case end-to-end:
- produces a transcript (in-process simulator, external web call, etc.)
- returns an optional judge verdict

Each implementation lives in its own module and registers itself in
:mod:`app.services.eval_engines.registry`. See ``docs/eval-engines.md`` for
the full how-to-add-an-engine guide.
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from sqlmodel import Session

from app.models.enums import AgentMode, EvaluationEngineKind, Platform

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.schemas import (
        EvaluationEngineConfig,
        JudgeVerdict,
        RunConfig,
    )
    from app.models.test_case import TestCase
    from app.services.orchestrator import TestCaseRunResult


@dataclass(frozen=True)
class EngineTestResult:
    """Outcome of an engine's connection/config test (the "Test URL" button)."""

    ok: bool
    message: str


@dataclass(frozen=True)
class EngineRunArgs:
    """Inputs the orchestrator hands to ``engine.run_test_case``.

    Fields mirror the snapshot captured on :class:`app.models.run.Run` plus
    the per-test-case state. Engines pick the subset they need.
    """

    test_case: TestCase
    run_config: RunConfig
    agent: Agent
    agent_id: uuid.UUID
    agent_platform: Platform | None
    agent_integration_id: uuid.UUID | None
    agent_platform_agent_id: str | None
    agent_endpoint_url: str | None
    agent_system_prompt: str | None
    agent_tools: list[dict[str, Any]] | None
    agent_mode: AgentMode
    agent_model: str | None
    agent_provider: str | None
    cancel_event: asyncio.Event | None


class EvalEngine(ABC):
    """Strategy that drives a test case through an evaluation pipeline."""

    KIND: ClassVar[EvaluationEngineKind]
    LABEL: ClassVar[str]
    DESCRIPTION: ClassVar[str]

    @abstractmethod
    def supported_for_platform(self, platform: Platform | None) -> bool:
        """Return True when this engine can be selected for an agent on ``platform``.

        ``platform`` is ``Agent.platform``; ``None`` means the agent has no platform
        recorded (legacy data). Implementations should be permissive for ``None``
        when it makes sense for backward compatibility.
        """

    @abstractmethod
    def validate_config(
        self,
        engine_config: EvaluationEngineConfig,
        agent: Agent,
        session: Session,
    ) -> None:
        """Raise :class:`ValueError` if the engine config is invalid for this agent.

        Called from CRUD validation paths so errors become 422s at the route layer.
        """

    @abstractmethod
    async def test_connection(
        self,
        engine_config: EvaluationEngineConfig,
        agent: Agent,
        session: Session,
    ) -> EngineTestResult:
        """Smoke-test the engine config against the agent (the "Test URL" button)."""

    @abstractmethod
    async def run_test_case(
        self,
        engine_config: EvaluationEngineConfig,
        args: EngineRunArgs,
        session: Session,
    ) -> tuple[TestCaseRunResult, JudgeVerdict | None]:
        """Execute a single test case and return ``(run_result, verdict)``."""
