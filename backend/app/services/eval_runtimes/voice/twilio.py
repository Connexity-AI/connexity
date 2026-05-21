"""Twilio + Pipecat voice runtime.

Creates a durable voice job, waits for the caller worker and user-side result
submission, then returns the submitted transcript to the orchestrator.
"""

import asyncio
import logging
import time
import uuid
from typing import ClassVar

from sqlmodel import Session

from app import crud
from app.core.db import engine
from app.models import VoiceSimulationJobCreate, VoiceSimulationJobUpdate
from app.models.agent import Agent
from app.models.enums import (
    Platform,
    RunMode,
    VoiceRuntimeKind,
    VoiceSimulationJobStatus,
)
from app.models.schemas import RunConfig, RuntimeConfig, TwilioVoiceRuntimeConfig
from app.services.dtmf import allocate_dtmf_code
from app.services.eval_runtimes.base import (
    EvalRuntime,
    RuntimeRunArgs,
    RuntimeTestResult,
)
from app.services.eval_runtimes.types import TestCaseRunResult
from app.services.voice_runtime_result import (
    assemble_test_case_run_result_from_voice_job,
)

logger = logging.getLogger(__name__)

_TERMINAL_FAILURE_STATUSES = (
    VoiceSimulationJobStatus.FAILED,
    VoiceSimulationJobStatus.EXPIRED,
    VoiceSimulationJobStatus.CANCELLED,
)

_DEFAULT_POLL_INTERVAL_SECONDS = 0.25


class TwilioVoiceRuntime(EvalRuntime):
    MODE: ClassVar[RunMode] = RunMode.VOICE
    KIND: ClassVar[VoiceRuntimeKind] = VoiceRuntimeKind.TWILIO
    LABEL: ClassVar[str] = "Twilio Voice"
    DESCRIPTION: ClassVar[str] = (
        "Place a Twilio call to the agent phone number and judge from the "
        "user-submitted transcript"
    )

    def supported_for_platform(self, platform: Platform | None) -> bool:
        return True

    def validate_config(
        self,
        runtime_config: RuntimeConfig,
        agent: Agent,
        session: Session,
    ) -> None:
        if not isinstance(runtime_config, TwilioVoiceRuntimeConfig):
            msg = "twilio voice runtime requires a TwilioVoiceRuntimeConfig"
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
            ok=True,
            message="Twilio voice runtime is available.",
        )

    async def run_test_case(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TestCaseRunResult:
        if not isinstance(runtime_config, TwilioVoiceRuntimeConfig):
            msg = "twilio voice runtime requires a TwilioVoiceRuntimeConfig"
            raise ValueError(msg)

        run_config = args.run_snapshot.run_config
        self._validate_run_config(run_config)

        assert run_config.agent_phone_number is not None
        assert run_config.user_simulator is not None
        assert run_config.user_simulator.stt is not None
        assert run_config.user_simulator.tts is not None
        assert run_config.max_call_duration_seconds is not None

        dtmf_code = allocate_dtmf_code(session=session)
        stt = run_config.user_simulator.stt
        tts = run_config.user_simulator.tts

        job = crud.create_voice_simulation_job(
            session=session,
            job_in=VoiceSimulationJobCreate(
                run_id=args.run_snapshot.run_id,
                test_case_id=args.test_case.id,
                test_case_result_id=args.test_case_result_id,
                repetition_index=args.repetition_index,
                dtmf_code=dtmf_code,
                agent_phone_number=run_config.agent_phone_number,
                stt_provider=stt.provider,
                stt_model=stt.model,
                tts_provider=tts.provider,
                tts_model=tts.model,
                tts_voice_id=tts.voice_id,
                max_call_duration_seconds=run_config.max_call_duration_seconds,
            ),
        )

        completed_job = await self._wait_for_job_completion(
            job_id=job.id,
            timeout_seconds=run_config.timeout_per_test_case_ms / 1000.0,
            cancel_event=args.run_snapshot.cancel_event,
        )
        return assemble_test_case_run_result_from_voice_job(completed_job)

    def _validate_run_config(self, run_config: RunConfig) -> None:
        if run_config.mode != RunMode.VOICE:
            msg = "Twilio voice runtime requires RunConfig.mode='voice'"
            raise ValueError(msg)
        if not (run_config.agent_phone_number or "").strip():
            msg = "agent_phone_number is required for voice runs"
            raise ValueError(msg)
        sim = run_config.user_simulator
        if sim is None or sim.stt is None:
            msg = "user_simulator.stt is required for voice runs"
            raise ValueError(msg)
        if sim.tts is None or not (sim.tts.voice_id or "").strip():
            msg = "user_simulator.tts with voice_id is required for voice runs"
            raise ValueError(msg)
        if run_config.max_call_duration_seconds is None:
            msg = "max_call_duration_seconds is required for voice runs"
            raise ValueError(msg)
        timeout_seconds = run_config.timeout_per_test_case_ms / 1000.0
        if run_config.max_call_duration_seconds >= timeout_seconds:
            msg = (
                "max_call_duration_seconds must be shorter than "
                "timeout_per_test_case_ms"
            )
            raise ValueError(msg)

    async def _wait_for_job_completion(
        self,
        *,
        job_id: uuid.UUID,
        timeout_seconds: float,
        cancel_event: asyncio.Event | None,
        poll_interval_seconds: float = _DEFAULT_POLL_INTERVAL_SECONDS,
    ):
        deadline = time.monotonic() + timeout_seconds

        while True:
            if cancel_event is not None and cancel_event.is_set():
                await asyncio.to_thread(self._mark_job_cancelled, job_id)
                msg = f"Voice simulation cancelled for job {job_id}"
                raise RuntimeError(msg)

            job = await asyncio.to_thread(self._fetch_job, job_id)
            if job is None:
                msg = f"Voice simulation job {job_id} not found"
                raise RuntimeError(msg)

            if job.status == VoiceSimulationJobStatus.COMPLETED:
                return job

            if job.status in _TERMINAL_FAILURE_STATUSES:
                detail = job.error_message or job.status.value
                msg = f"Voice simulation failed for job {job_id}: {detail}"
                raise RuntimeError(msg)

            if time.monotonic() >= deadline:
                await asyncio.to_thread(
                    self._mark_job_failed,
                    job_id,
                    "Timed out waiting for voice simulation result",
                )
                msg = (
                    f"Voice simulation timed out after {timeout_seconds:.0f}s "
                    f"for job {job_id}"
                )
                raise TimeoutError(msg)

            await asyncio.sleep(poll_interval_seconds)

    @staticmethod
    def _fetch_job(job_id: uuid.UUID):
        with Session(engine) as session:
            return crud.get_voice_simulation_job(session=session, job_id=job_id)

    @staticmethod
    def _mark_job_cancelled(job_id: uuid.UUID) -> None:
        with Session(engine) as session:
            job = crud.get_voice_simulation_job(session=session, job_id=job_id)
            if job is None:
                return
            if job.status in (
                VoiceSimulationJobStatus.COMPLETED,
                *_TERMINAL_FAILURE_STATUSES,
            ):
                return
            crud.update_voice_simulation_job(
                session=session,
                db_job=job,
                job_in=VoiceSimulationJobUpdate(
                    status=VoiceSimulationJobStatus.CANCELLED,
                    error_code="CANCELLED",
                    error_message="Run cancelled while waiting for voice result",
                ),
            )

    @staticmethod
    def _mark_job_failed(job_id: uuid.UUID, error_message: str) -> None:
        with Session(engine) as session:
            job = crud.get_voice_simulation_job(session=session, job_id=job_id)
            if job is None:
                return
            if job.status == VoiceSimulationJobStatus.COMPLETED:
                return
            crud.update_voice_simulation_job(
                session=session,
                db_job=job,
                job_in=VoiceSimulationJobUpdate(
                    status=VoiceSimulationJobStatus.FAILED,
                    error_code="RESULT_TIMEOUT",
                    error_message=error_message,
                ),
            )
