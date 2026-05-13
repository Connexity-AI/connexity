"""Retell evaluation engine.

Runs Retell simulation tests for each test case, maps the generated transcript
into Connexity's :class:`ConversationTurn` shape, and runs the existing
Connexity judge over it.

Retell credentials and the Retell agent id come from the eval-config agent's
Retell integration setup (see ``Agent`` + ``Integration``). The engine
fails the test case with a clear error if that setup is missing or stale.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from app.services.orchestrator import TestCaseRunResult

from sqlmodel import Session

from app.core.encryption import decrypt
from app.models.agent import Agent
from app.models.enums import EvaluationEngineKind, Platform, TurnRole
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
from app.services.eval_engines.retell_mapping import (
    build_retell_dynamic_variables,
    build_retell_metrics,
    build_retell_user_prompt,
    map_retell_transcript_snapshot,
)
from app.services.judge import JudgeInput, evaluate_transcript
from app.services.retell import (
    RetellCall,
    RetellTestCaseJob,
    create_retell_batch_test,
    create_retell_test_case_definition,
    get_retell_agent_response_engine,
    get_retell_batch_test,
    get_retell_call,
    list_retell_test_runs,
    test_retell_connection,
)

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 2.0
_DEFAULT_POLL_TIMEOUT_SECONDS = 120.0
_PROMPT_LOG_MAX_CHARS = 1200


class RetellEngineError(Exception):
    """Raised when the Retell eval pipeline cannot proceed (missing creds, etc.)."""


def _resolve_retell_integration(
    *,
    session: Session,
    agent_platform: Platform | None,
    agent_integration_id: uuid.UUID | None,
    agent_platform_agent_id: str | None,
) -> tuple[Integration, str]:
    """Return ``(integration, retell_agent_id)`` for ``agent``'s Retell target.

    Raises :class:`RetellEngineError` if the agent has no Retell target or
    the linked integration is missing.
    """
    if agent_platform != Platform.RETELL:
        raise RetellEngineError(
            "Agent has no Retell target configured. "
            "Add a Retell integration on the agent setup page first."
        )
    if agent_integration_id is None or agent_platform_agent_id is None:
        raise RetellEngineError(
            "Retell target is missing an integration or platform agent id."
        )
    integration = session.get(Integration, agent_integration_id)
    if integration is None:
        raise RetellEngineError("Linked Retell integration not found.")
    return integration, agent_platform_agent_id


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
            if status == "error":
                disconnection_reason = (
                    str(call.raw.get("disconnection_reason"))
                    if isinstance(call.raw, dict)
                    and call.raw.get("disconnection_reason") is not None
                    else None
                )
                if disconnection_reason:
                    raise RetellEngineError(
                        f"Retell call {call_id} ended with error: {disconnection_reason}"
                    )
                raise RetellEngineError(f"Retell call {call_id} ended with error")
            if status in {"ended", "completed", "finished"}:
                return call

        if time.monotonic() >= deadline:
            raise RetellEngineError(
                f"Retell call {call_id} did not finish within {timeout_seconds:.0f}s"
            )
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


async def wait_for_retell_test_run_completion(
    *,
    api_key: str,
    batch_test_id: str,
    test_case_definition_id: str,
    timeout_seconds: float,
    cancel_event: asyncio.Event | None,
) -> RetellTestCaseJob:
    deadline = time.monotonic() + timeout_seconds
    while True:
        if cancel_event is not None and cancel_event.is_set():
            raise RetellEngineError("Run cancelled while waiting on Retell simulation")

        batch = await get_retell_batch_test(
            api_key=api_key, batch_test_id=batch_test_id
        )
        logger.info(
            "Retell simulation batch poll: batch_id=%s status=%s pass=%s fail=%s error=%s total=%s",
            batch_test_id,
            batch.status,
            batch.pass_count,
            batch.fail_count,
            batch.error_count,
            batch.total_count,
        )
        if batch.status == "complete":
            jobs = await list_retell_test_runs(
                api_key=api_key, batch_test_id=batch_test_id
            )
            for job in jobs:
                if job.test_case_definition_id != test_case_definition_id:
                    continue
                logger.info(
                    "Retell simulation job terminal state: batch_id=%s test_definition_id=%s job_id=%s status=%s explanation=%s",
                    batch_test_id,
                    test_case_definition_id,
                    job.test_case_job_id,
                    job.status,
                    job.result_explanation,
                )
                if job.status == "error":
                    detail = job.result_explanation or "Retell simulation returned error"
                    if job.transcript_snapshot:
                        logger.info(
                            "Retell simulation error transcript snapshot: batch_id=%s job_id=%s transcript_snapshot=%s",
                            batch_test_id,
                            job.test_case_job_id,
                            job.transcript_snapshot,
                        )
                        logger.warning(
                            "Retell simulation job returned error with transcript; continuing to Connexity judge: batch_id=%s job_id=%s explanation=%s",
                            batch_test_id,
                            job.test_case_job_id,
                            detail,
                        )
                        return job
                    raise RetellEngineError(
                        f"Retell simulation job {job.test_case_job_id} failed: {detail}"
                    )
                if job.status in {"pass", "fail"}:
                    return job

        if time.monotonic() >= deadline:
            raise RetellEngineError(
                "Retell simulation did not finish within "
                f"{timeout_seconds:.0f}s for batch {batch_test_id}"
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
            _resolve_retell_integration(
                session=session,
                agent_platform=agent.platform,
                agent_integration_id=agent.integration_id,
                agent_platform_agent_id=agent.platform_agent_id,
            )
        except RetellEngineError as exc:
            raise ValueError(str(exc)) from exc

    async def test_connection(
        self,
        engine_config: EvaluationEngineConfig,
        agent: Agent,
        session: Session,
    ) -> EngineTestResult:
        try:
            integration, _ = _resolve_retell_integration(
                session=session,
                agent_platform=agent.platform,
                agent_integration_id=agent.integration_id,
                agent_platform_agent_id=agent.platform_agent_id,
            )
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
                session=session,
                agent_platform=args.agent_platform,
                agent_integration_id=args.agent_integration_id,
                agent_platform_agent_id=args.agent_platform_agent_id,
            )
            api_key = decrypt(integration.encrypted_api_key)
        except (RetellEngineError, Exception) as exc:  # noqa: BLE001
            logger.warning(
                "Retell engine setup failed for agent %s: %s", args.agent_id, exc
            )
            raise

        response_engine = await get_retell_agent_response_engine(
            api_key=api_key,
            retell_agent_id=retell_agent_id,
        )
        user_prompt = build_retell_user_prompt(
            args.test_case, max_turns=args.run_config.max_turns
        )
        metrics = build_retell_metrics(args.test_case)
        dynamic_variables = build_retell_dynamic_variables(args.test_case)
        logger.info(
            "Retell simulation setup: agent_id=%s retell_agent_id=%s test_case_id=%s response_engine=%s metrics=%s prompt_chars=%s prompt_preview=%s",
            args.agent_id,
            retell_agent_id,
            args.test_case.id,
            response_engine,
            metrics,
            len(user_prompt),
            user_prompt[:_PROMPT_LOG_MAX_CHARS],
        )
        test_case_definition_id = await create_retell_test_case_definition(
            api_key=api_key,
            response_engine=response_engine,
            name=args.test_case.name or str(args.test_case.id),
            user_prompt=user_prompt,
            metrics=metrics,
            dynamic_variables=dynamic_variables,
        )
        logger.info(
            "Retell simulation test definition created: test_case_id=%s test_definition_id=%s",
            args.test_case.id,
            test_case_definition_id,
        )
        batch_test_id = await create_retell_batch_test(
            api_key=api_key,
            response_engine=response_engine,
            test_case_definition_ids=[test_case_definition_id],
        )
        logger.info(
            "Retell simulation batch created: test_case_id=%s test_definition_id=%s batch_id=%s",
            args.test_case.id,
            test_case_definition_id,
            batch_test_id,
        )
        timeout_seconds = max(10.0, args.run_config.timeout_per_test_case_ms / 1000.0)
        job = await wait_for_retell_test_run_completion(
            api_key=api_key,
            batch_test_id=batch_test_id,
            test_case_definition_id=test_case_definition_id,
            timeout_seconds=timeout_seconds,
            cancel_event=args.cancel_event,
        )

        transcript = map_retell_transcript_snapshot(job.transcript_snapshot)
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
