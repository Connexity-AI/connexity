"""Custom URL evaluation engine.

Runs the standard Connexity simulator + judge, but points the agent HTTP call at
a user-provided URL instead of the agent's own ``endpoint_url``. The URL must
honor Connexity's OpenAI-compatible chat-completions contract — see
:mod:`app.models.agent_contract` for ``AgentRequest`` / ``AgentResponse``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

import httpx
from sqlmodel import Session

if TYPE_CHECKING:
    from app.services.orchestrator import TestCaseRunResult

from app.models.agent import Agent
from app.models.agent_contract import AgentRequest, AgentResponse, ChatMessage
from app.models.enums import AgentMode, EvaluationEngineKind, Platform, TurnRole
from app.models.schemas import (
    CustomUrlEngineConfig,
    EvaluationEngineConfig,
    JudgeVerdict,
)
from app.services.eval_engines.base import (
    EngineRunArgs,
    EngineTestResult,
    EvalEngine,
)

logger = logging.getLogger(__name__)

_TEST_TIMEOUT_SECONDS = 10.0


class CustomUrlEngine(EvalEngine):
    KIND: ClassVar[EvaluationEngineKind] = EvaluationEngineKind.CUSTOM_URL
    LABEL: ClassVar[str] = "Your Agent"
    DESCRIPTION: ClassVar[str] = "Run evaluations against your own agent"

    def supported_for_platform(self, platform: Platform | None) -> bool:
        # "Custom" agents are stored as Platform.WEBHOOK; ``None`` covers legacy
        # rows that pre-date the platform column.
        return platform in (None, Platform.WEBHOOK)

    def validate_config(
        self,
        engine_config: EvaluationEngineConfig,
        agent: Agent,
        session: Session,
    ) -> None:
        if not isinstance(engine_config, CustomUrlEngineConfig):
            msg = "custom_url engine requires a CustomUrlEngineConfig"
            raise ValueError(msg)
        url = engine_config.url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            msg = "url must start with http:// or https://"
            raise ValueError(msg)

    async def test_connection(
        self,
        engine_config: EvaluationEngineConfig,
        agent: Agent,
        session: Session,
    ) -> EngineTestResult:
        if not isinstance(engine_config, CustomUrlEngineConfig):
            return EngineTestResult(
                ok=False,
                message="Internal error: wrong engine config type",
            )

        probe = AgentRequest(messages=[ChatMessage(role=TurnRole.USER, content="ping")])
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    engine_config.url,
                    json=probe.model_dump(mode="json", exclude_none=True),
                    timeout=_TEST_TIMEOUT_SECONDS,
                )
        except httpx.HTTPError as exc:
            return EngineTestResult(ok=False, message=f"Network error: {exc}")

        if response.status_code >= 400:
            return EngineTestResult(
                ok=False,
                message=f"HTTP {response.status_code} from URL",
            )

        try:
            AgentResponse.model_validate(response.json())
        except ValueError as exc:
            return EngineTestResult(
                ok=False,
                message=f"Response does not match AgentResponse contract: {exc}",
            )

        return EngineTestResult(
            ok=True, message="URL responded with a valid AgentResponse."
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

        if not isinstance(engine_config, CustomUrlEngineConfig):
            msg = "custom_url engine requires a CustomUrlEngineConfig"
            raise ValueError(msg)

        # Override the agent endpoint URL with the configured one and force
        # ENDPOINT mode regardless of the agent's stored mode.
        return await run_test_case_with_evaluation(
            args.test_case,
            engine_config.url,
            args.run_config,
            agent_mode=AgentMode.ENDPOINT,
            agent_model=args.agent_model,
            agent_provider=args.agent_provider,
            agent_system_prompt=args.agent_system_prompt,
            agent_tools=args.agent_tools,
            cancel_event=args.cancel_event,
        )
