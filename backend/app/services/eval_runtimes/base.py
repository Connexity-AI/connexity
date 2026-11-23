"""Evaluation runtime abstraction.

An evaluation runtime is the strategy that drives a single test case to a
transcript. The runner owns concurrency, judging, persistence, and
aggregate metrics; the runtime owns the conversation loop (in-process
simulator, phone call, etc.).

Each implementation lives in its own module and registers itself in
:mod:`app.services.eval_runtimes.registry`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from sqlmodel import Session

from app.models.enums import RunMode, TextRuntimeKind
from app.models.schemas import RuntimeConfig
from app.models.test_case import TestCase
from app.services.eval_runtimes.types import (
    AgentSnapshot,
    RunSnapshot,
    TestCaseRunResult,
)


@dataclass(frozen=True)
class RuntimeRunArgs:
    """Inputs the runner hands to ``runtime.run_test_case``."""

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
    async def run_test_case(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TestCaseRunResult:
        """Execute a single test case and return its transcript and metadata.

        The runner runs the judge and persists results; runtimes should
        not call the judge directly.
        """
