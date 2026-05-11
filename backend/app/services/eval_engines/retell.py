"""Retell evaluation engine.

Drives a Retell web call for each test case, polls until the call ends, then
maps the Retell transcript into Connexity's :class:`ConversationTurn` shape and
runs the existing Connexity judge over it.

Retell credentials and the Retell agent id come from the eval-config agent's
Retell integration setup (see ``Environment`` + ``Integration``). The engine
fails the test case with a clear error if that setup is missing or stale.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from app.services.orchestrator import TestCaseRunResult

from sqlmodel import Session, select

from app.core.encryption import decrypt
from app.models.agent import Agent
from app.models.enums import EvaluationEngineKind, Platform, TurnRole
from app.models.environment import Environment
from app.models.integration import Integration
from app.models.schemas import (
    ConversationTurn,
    EvaluationEngineConfig,
    JudgeVerdict,
    RetellEngineConfig,
)
from app.services.eval_engines.base import (
    EngineRunArgs,
    EngineTestResult,
    EvalEngine,
)
from app.services.judge import JudgeInput, evaluate_transcript
from app.services.retell import (
    RetellCall,
    create_retell_web_call,
    get_retell_call,
    test_retell_connection,
)

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 2.0
_DEFAULT_POLL_TIMEOUT_SECONDS = 120.0


class RetellEngineError(Exception):
    """Raised when the Retell eval pipeline cannot proceed (missing creds, etc.)."""


def _resolve_retell_integration(
    *, session: Session, agent: Agent
) -> tuple[Integration, str]:
    """Return ``(integration, retell_agent_id)`` for ``agent``'s Retell env.

    Raises :class:`RetellEngineError` if the agent has no Retell environment or
    the linked integration is missing.
    """
    env = session.exec(
        select(Environment).where(
            Environment.agent_id == agent.id,
            Environment.platform == Platform.RETELL,
        )
    ).first()
    if env is None:
        raise RetellEngineError(
            "Agent has no Retell environment configured. "
            "Add a Retell integration on the agent setup page first."
        )
    if env.integration_id is None or env.platform_agent_id is None:
        raise RetellEngineError(
            "Retell environment is missing an integration or platform agent id."
        )
    integration = session.get(Integration, env.integration_id)
    if integration is None:
        raise RetellEngineError("Linked Retell integration not found.")
    return integration, env.platform_agent_id


def _map_retell_transcript(call: RetellCall) -> list[ConversationTurn]:
    """Map ``call.transcript_object`` (Retell's shape) to ConversationTurns."""
    out: list[ConversationTurn] = []
    if not call.transcript_object:
        return out
    base_ms = call.start_timestamp or 0
    for index, item in enumerate(call.transcript_object):
        if not isinstance(item, dict):
            continue
        raw_role = str(item.get("role") or "").lower()
        if raw_role == "agent":
            role = TurnRole.ASSISTANT
        elif raw_role == "user":
            role = TurnRole.USER
        else:
            continue
        content = item.get("content")
        if not isinstance(content, str):
            continue
        # Retell does not surface per-turn timestamps; spread evenly using start.
        ts_seconds = (base_ms + index) / 1000.0 if base_ms else time.time()
        out.append(
            ConversationTurn(
                index=index,
                role=role,
                content=content,
                timestamp=datetime.fromtimestamp(ts_seconds, tz=UTC),
            )
        )
    return out


async def _wait_for_call_completion(
    *,
    api_key: str,
    call_id: str,
    timeout_seconds: float,
    cancel_event: asyncio.Event | None,
) -> RetellCall:
    """Poll until the Retell call ends or ``timeout_seconds`` elapses."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        if cancel_event is not None and cancel_event.is_set():
            raise RetellEngineError("Run cancelled while waiting on Retell call")

        call = await get_retell_call(api_key, call_id)
        if call is not None:
            status = (call.call_status or "").lower()
            if status in {"ended", "completed", "finished"}:
                return call

        if time.monotonic() >= deadline:
            raise RetellEngineError(
                f"Retell call {call_id} did not finish within {timeout_seconds:.0f}s"
            )
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


class RetellEngine(EvalEngine):
    KIND: ClassVar[EvaluationEngineKind] = EvaluationEngineKind.RETELL
    LABEL: ClassVar[str] = "Retell"
    DESCRIPTION: ClassVar[str] = "Run evaluations using Retell"

    def supported_for_platform(self, platform: Platform | None) -> bool:
        return platform == Platform.RETELL

    def validate_config(
        self,
        engine_config: EvaluationEngineConfig,
        agent: Agent,
        session: Session,
    ) -> None:
        if not isinstance(engine_config, RetellEngineConfig):
            msg = "retell engine requires a RetellEngineConfig"
            raise ValueError(msg)
        try:
            _resolve_retell_integration(session=session, agent=agent)
        except RetellEngineError as exc:
            raise ValueError(str(exc)) from exc

    async def test_connection(
        self,
        engine_config: EvaluationEngineConfig,
        agent: Agent,
        session: Session,
    ) -> EngineTestResult:
        try:
            integration, _ = _resolve_retell_integration(session=session, agent=agent)
        except RetellEngineError as exc:
            return EngineTestResult(ok=False, message=str(exc))
        try:
            api_key = decrypt(integration.encrypted_api_key)
        except Exception as exc:  # noqa: BLE001 - surface as failed test
            return EngineTestResult(
                ok=False, message=f"Could not decrypt Retell API key: {exc}"
            )
        ok = await test_retell_connection(api_key)
        if not ok:
            return EngineTestResult(
                ok=False, message="Retell API rejected the configured API key"
            )
        return EngineTestResult(
            ok=True, message="Retell integration is reachable and authorised."
        )

    async def run_test_case(
        self,
        engine_config: EvaluationEngineConfig,
        args: EngineRunArgs,
        session: Session,
    ) -> tuple[TestCaseRunResult, JudgeVerdict | None]:
        from app.services.orchestrator import TestCaseRunResult  # noqa: F811

        if not isinstance(engine_config, RetellEngineConfig):
            msg = "retell engine requires a RetellEngineConfig"
            raise ValueError(msg)

        try:
            integration, retell_agent_id = _resolve_retell_integration(
                session=session, agent=args.agent
            )
            api_key = decrypt(integration.encrypted_api_key)
        except (RetellEngineError, Exception) as exc:  # noqa: BLE001
            logger.warning(
                "Retell engine setup failed for agent %s: %s", args.agent.id, exc
            )
            raise

        dynamic_vars: dict[str, str] = {
            "test_case_id": str(args.test_case.id),
            "test_case_name": args.test_case.name or "",
            "persona_context": args.test_case.persona_context or "",
            "first_message": args.test_case.first_message or "",
        }
        create_result = await create_retell_web_call(
            api_key=api_key,
            retell_agent_id=retell_agent_id,
            dynamic_variables=dynamic_vars,
        )
        if not create_result.success or not create_result.call_id:
            raise RetellEngineError(
                create_result.error_message or "Failed to create Retell web call"
            )

        timeout_seconds = max(10.0, args.run_config.timeout_per_test_case_ms / 1000.0)
        call = await _wait_for_call_completion(
            api_key=api_key,
            call_id=create_result.call_id,
            timeout_seconds=timeout_seconds,
            cancel_event=args.cancel_event,
        )

        transcript = _map_retell_transcript(call)
        run_result = TestCaseRunResult(
            transcript=transcript,
            agent_token_usage={},
            platform_token_usage={},
        )

        if not transcript:
            return run_result, None

        verdict = await evaluate_transcript(
            JudgeInput(
                transcript=transcript,
                test_case=args.test_case,
                agent_system_prompt=args.agent_system_prompt,
                agent_tools=args.agent_tools,
                judge_config=args.run_config.judge,
            )
        )
        return run_result, verdict
