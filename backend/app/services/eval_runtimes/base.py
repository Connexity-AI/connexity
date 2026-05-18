"""Evaluation runtime abstraction.

An evaluation runtime is the strategy that drives a single test case to a
transcript. The orchestrator owns concurrency, judging, persistence, and
aggregate metrics; the runtime owns the conversation loop (in-process
simulator, phone call, etc.).

Each implementation lives in its own module and registers itself in
:mod:`app.services.eval_runtimes.registry`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from sqlmodel import Session

from app.models.agent import Agent
from app.models.enums import Platform, RunMode, TextRuntimeKind
from app.models.schemas import RuntimeConfig
from app.models.test_case import TestCase
from app.services.eval_runtimes.types import (
    AgentSnapshot,
    RunSnapshot,
    TestCaseRunResult,
)


@dataclass(frozen=True)
class RuntimeTestResult:
    """Outcome of a runtime's connection/config test."""

    ok: bool
    message: str


@dataclass(frozen=True)
class RuntimeRunArgs:
    """Inputs the orchestrator hands to ``runtime.run_test_case``."""

    test_case: TestCase
    agent_snapshot: AgentSnapshot
    run_snapshot: RunSnapshot


class EvalRuntime(ABC):
    """Strategy that drives a test case end-to-end to a transcript."""

    MODE: ClassVar[RunMode]
    KIND: ClassVar[TextRuntimeKind]
    LABEL: ClassVar[str]
    DESCRIPTION: ClassVar[str]

    @abstractmethod
    def supported_for_platform(self, platform: Platform | None) -> bool:
        """Return True when this runtime can be selected for an agent on ``platform``.

        ``platform`` is ``Agent.platform``; ``None`` means the agent has no platform
        recorded (legacy data). Implementations should be permissive for ``None``
        when it makes sense for backward compatibility.
        """

    @abstractmethod
    def validate_config(
        self,
        runtime_config: RuntimeConfig,
        agent: Agent,
        session: Session,
    ) -> None:
        """Raise :class:`ValueError` if the runtime config is invalid for this agent.

        Called from CRUD validation paths so errors become 422s at the route layer.
        """

    @abstractmethod
    async def test_connection(
        self,
        runtime_config: RuntimeConfig,
        agent: Agent,
        session: Session,
    ) -> RuntimeTestResult:
        """Smoke-test the runtime config against the agent."""

    @abstractmethod
    async def run_test_case(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TestCaseRunResult:
        """Execute a single test case and return its transcript and metadata.

        The orchestrator runs the judge and persists results; runtimes should
        not call the judge directly.
        """
