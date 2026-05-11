"""Connexity (native) evaluation engine.

Runs the in-process user simulator against the agent, captures the transcript,
and scores it with the Connexity judge. This is the original behaviour — the
engine wraps :func:`app.services.orchestrator.run_test_case_with_evaluation`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Session

from app.models.agent import Agent
from app.models.enums import EvaluationEngineKind, Platform
from app.models.schemas import EvaluationEngineConfig, JudgeVerdict
from app.services.eval_engines.base import (
    EngineRunArgs,
    EngineTestResult,
    EvalEngine,
)

if TYPE_CHECKING:
    from app.services.orchestrator import TestCaseRunResult


class ConnexityEngine(EvalEngine):
    KIND: ClassVar[EvaluationEngineKind] = EvaluationEngineKind.CONNEXITY
    LABEL: ClassVar[str] = "Connexity"
    DESCRIPTION: ClassVar[str] = "Run evaluations using Connexity"

    def supported_for_platform(self, platform: Platform | None) -> bool:
        return True

    def validate_config(
        self,
        engine_config: EvaluationEngineConfig,
        agent: Agent,
        session: Session,
    ) -> None:
        return None

    async def test_connection(
        self,
        engine_config: EvaluationEngineConfig,
        agent: Agent,
        session: Session,
    ) -> EngineTestResult:
        return EngineTestResult(
            ok=True, message="Connexity engine is always available."
        )

    async def run_test_case(
        self,
        engine_config: EvaluationEngineConfig,
        args: EngineRunArgs,
        session: Session,
    ) -> tuple[TestCaseRunResult, JudgeVerdict | None]:
        from app.services.orchestrator import (  # local import to avoid cycle
            run_test_case_with_evaluation,
        )

        return await run_test_case_with_evaluation(
            args.test_case,
            args.agent_endpoint_url,
            args.run_config,
            agent_mode=args.agent_mode,
            agent_model=args.agent_model,
            agent_provider=args.agent_provider,
            agent_system_prompt=args.agent_system_prompt,
            agent_tools=args.agent_tools,
            cancel_event=args.cancel_event,
        )
