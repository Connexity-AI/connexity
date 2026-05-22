"""Poll Postgres for pending voice jobs, dial Twilio, and wait for `/ws` completion."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from app import crud
from app.core.config import settings as connexity_settings
from app.core.db import engine
from app.models import VoiceSimulationJobUpdate
from app.models.enums import VoiceSimulationJobStatus
from app.models.voice_simulation_job import VoiceSimulationJob
from sqlmodel import Session

import voice_runner.active_calls as active_calls
from voice_runner.public_urls import twiml_http_url
from voice_runner.settings import WorkerSettings, computed_worker_id, lease_ttl_seconds
from voice_runner.twilio_voice import create_outbound_call, hangup_call

logger = logging.getLogger(__name__)

_CALL_MUTEX = asyncio.Lock()


def _fail_job(job_id: uuid.UUID, *, code: str, message: str) -> None:
    with Session(engine) as session:
        job = crud.get_voice_simulation_job(session=session, job_id=job_id)
        if job is None:
            return
        crud.update_voice_simulation_job(
            session=session,
            db_job=job,
            job_in=VoiceSimulationJobUpdate(
                status=VoiceSimulationJobStatus.FAILED,
                error_code=code,
                error_message=message,
                lease_expires_at=None,
            ),
        )


def _job_is_cancelled(job_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        job = crud.get_voice_simulation_job(session=session, job_id=job_id)
        return job is not None and job.status == VoiceSimulationJobStatus.CANCELLED


async def worker_loop(stop: asyncio.Event, worker_settings: WorkerSettings) -> None:
    """Poll Postgres and run calls in loop mode (local Docker).

    Kubernetes one-shot mode (claim one job then exit) is planned for step 11.
    """
    if not connexity_settings.twilio_voice_runtime_configured():
        logger.error(
            "Twilio is not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
            "and TWILIO_FROM_NUMBER."
        )
        return

    public_raw = (worker_settings.VOICE_PUBLIC_BASE_URL or "").strip().rstrip("/")
    if not public_raw:
        logger.error(
            "VOICE_PUBLIC_BASE_URL must be configured for Twilio webhook callbacks."
        )
        return

    wid = computed_worker_id(worker_settings)
    logger.info("Voice worker started worker_id=%s", wid)

    while not stop.is_set():
        claimed_job: VoiceSimulationJob | None = None

        async with _CALL_MUTEX:
            with Session(engine) as session:
                pending = crud.claim_next_pending_voice_job(
                    session=session,
                    worker_id=wid,
                    lease_seconds=worker_settings.VOICE_JOB_LEASE_FLOOR_SECONDS,
                )
                if pending is not None:
                    ttl = lease_ttl_seconds(
                        max_call_duration_seconds=pending.max_call_duration_seconds,
                        settings=worker_settings,
                    )
                    crud.update_voice_simulation_job(
                        session=session,
                        db_job=pending,
                        job_in=VoiceSimulationJobUpdate(
                            lease_expires_at=datetime.now(UTC) + timedelta(seconds=ttl)
                        ),
                    )
                    claimed_job = pending

        if claimed_job is None:
            await asyncio.wait(
                [
                    asyncio.create_task(stop.wait()),
                    asyncio.create_task(
                        asyncio.sleep(worker_settings.VOICE_WORKER_POLL_IDLE_SECONDS)
                    ),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            continue

        job_id = claimed_job.id
        loop = asyncio.get_running_loop()
        done_future: asyncio.Future[None] = loop.create_future()
        stream_ev = active_calls.STREAM_REGISTRY.register(job_id)
        active_calls.CALL_COMPLETION.register(job_id, done_future)

        dial_sid: str | None = None

        if _job_is_cancelled(job_id):
            logger.info("Skipping cancelled job=%s before dial", job_id)
            active_calls.STREAM_REGISTRY.forget(job_id)
            active_calls.CALL_COMPLETION.cancel(job_id)
            continue

        try:
            active_calls.EXPECTED_JOB_ID = job_id
            webhook = twiml_http_url(public_base=public_raw, job_id=str(job_id))

            sid = connexity_settings.TWILIO_ACCOUNT_SID
            tok = connexity_settings.TWILIO_AUTH_TOKEN
            frm = connexity_settings.TWILIO_FROM_NUMBER
            assert sid and tok and frm

            try:
                dial_sid = await create_outbound_call(
                    account_sid=sid,
                    auth_token=tok,
                    from_number=str(frm),
                    to_number=claimed_job.agent_phone_number,
                    twiml_url=webhook,
                )
            except Exception as exc:  # noqa: BLE001 — Twilio client errors vary
                logger.exception("Twilio dial failed job=%s", job_id)
                _fail_job(
                    job_id,
                    code="twilio_dial_failed",
                    message=str(exc),
                )
                active_calls.STREAM_REGISTRY.forget(job_id)
                active_calls.CALL_COMPLETION.cancel(job_id)
                continue

            with Session(engine) as session:
                refreshed = session.get(VoiceSimulationJob, job_id)
                if refreshed is None:
                    active_calls.STREAM_REGISTRY.forget(job_id)
                    active_calls.CALL_COMPLETION.cancel(job_id)
                    continue
                crud.update_voice_simulation_job(
                    session=session,
                    db_job=refreshed,
                    job_in=VoiceSimulationJobUpdate(twilio_call_sid=dial_sid),
                )

            if _job_is_cancelled(job_id):
                logger.info("Hanging up cancelled job=%s call_sid=%s", job_id, dial_sid)
                await hangup_call(account_sid=sid, auth_token=tok, call_sid=dial_sid)
                active_calls.CALL_COMPLETION.cancel(job_id)
                continue

            active_calls.register_active_call(job_id=job_id, call_sid=dial_sid)

            try:
                await asyncio.wait_for(
                    stream_ev.wait(),
                    timeout=worker_settings.VOICE_WORKER_CONNECT_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.error(
                    "Timed out waiting for Twilio Media Stream job=%s call_sid=%s",
                    job_id,
                    dial_sid,
                )
                _fail_job(
                    job_id,
                    code="twilio_media_stream_timeout",
                    message=(
                        "Twilio never opened the bidirectional Media Stream websocket "
                        f"within {worker_settings.VOICE_WORKER_CONNECT_TIMEOUT_SECONDS}s"
                    ),
                )
                await hangup_call(account_sid=sid, auth_token=tok, call_sid=dial_sid)
                active_calls.CALL_COMPLETION.cancel(job_id)
                continue

            await done_future
        except asyncio.CancelledError:
            sid = connexity_settings.TWILIO_ACCOUNT_SID
            tok = connexity_settings.TWILIO_AUTH_TOKEN
            if dial_sid is not None and sid and tok:
                await hangup_call(account_sid=sid, auth_token=tok, call_sid=dial_sid)
            _fail_job(
                job_id,
                code="worker_shutdown",
                message="Voice worker stopped during an active call.",
            )
            raise
        except Exception:
            logger.exception("Unexpected worker failure job=%s", job_id)
            _fail_job(
                job_id,
                code="voice_worker_internal_error",
                message="Unexpected worker crash after dial; see voice-worker logs.",
            )
            sid = connexity_settings.TWILIO_ACCOUNT_SID
            tok = connexity_settings.TWILIO_AUTH_TOKEN
            if dial_sid is not None and sid and tok:
                await hangup_call(account_sid=sid, auth_token=tok, call_sid=dial_sid)
        finally:
            active_calls.EXPECTED_JOB_ID = None
            active_calls.clear_active_call()
            active_calls.STREAM_REGISTRY.forget(job_id)
