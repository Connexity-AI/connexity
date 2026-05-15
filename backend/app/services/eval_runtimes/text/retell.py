"""Retell text runtime placeholder.

The previous implementation delegated the whole simulation to Retell batch
testing. The intended runtime keeps Connexity in control of user simulation and
uses Retell only for agent turns via chat APIs.
"""

from typing import ClassVar

from sqlmodel import Session

from app.models.agent import Agent
from app.models.enums import Platform, RunMode, TextRuntimeKind
from app.models.schemas import RetellRuntimeConfig, RuntimeConfig
from app.services.eval_runtimes.base import (
    EvalRuntime,
    RuntimeRunArgs,
    RuntimeTestResult,
)
from app.services.eval_runtimes.types import TestCaseRunResult


class RetellRuntimeNotImplementedError(NotImplementedError):
    """Raised until the Retell chat-completion runtime is implemented."""


class RetellRuntime(EvalRuntime):
    MODE: ClassVar[RunMode] = RunMode.TEXT
    KIND: ClassVar[TextRuntimeKind] = TextRuntimeKind.RETELL
    LABEL: ClassVar[str] = "Retell"
    DESCRIPTION: ClassVar[str] = "Run evaluations using Retell"

    def supported_for_platform(self, platform: Platform | None) -> bool:
        return platform == Platform.RETELL

    def validate_config(
        self,
        runtime_config: RuntimeConfig,
        agent: Agent,
        session: Session,
    ) -> None:
        if not isinstance(runtime_config, RetellRuntimeConfig):
            msg = "retell runtime requires a RetellRuntimeConfig"
            raise ValueError(msg)
        if agent.platform != Platform.RETELL:
            msg = "Retell runtime requires a Retell agent."
            raise ValueError(msg)
        if agent.integration_id is None or agent.platform_agent_id is None:
            msg = "Retell runtime requires an integration and platform agent id."
            raise ValueError(msg)

    async def test_connection(
        self,
        runtime_config: RuntimeConfig,
        agent: Agent,
        session: Session,
    ) -> RuntimeTestResult:
        try:
            self.validate_config(runtime_config, agent, session)
        except ValueError as exc:
            return RuntimeTestResult(ok=False, message=str(exc))
        return RuntimeTestResult(
            ok=False,
            message="Retell text runtime is not implemented yet.",
        )

    async def run_test_case(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TestCaseRunResult:
        msg = (
            "Retell text runtime is not implemented yet. It should use Retell "
            "create-chat and create-chat-completion APIs for agent turns."
        )
        raise RetellRuntimeNotImplementedError(msg)
