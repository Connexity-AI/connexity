"""HTTP + WebSocket entrypoints for Pipecat + Twilio, plus Postgres job polling."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from xml.sax.saxutils import escape

from app import crud
from app.core.config import settings as connexity_settings
from app.core.db import engine
from app.models import VoiceSimulationJobUpdate
from app.models.enums import VoiceSimulationJobStatus
from app.models.run import Run
from app.models.schemas import RunConfig
from app.models.test_case import TestCase
from app.models.voice_simulation_job import VoiceSimulationJob
from fastapi import FastAPI, WebSocket
from fastapi.responses import Response
from sqlmodel import Session

import voice_runner.active_calls as active_calls
from voice_runner.bot.pipeline import run_pipecat_voice_call
from voice_runner.public_urls import media_stream_wss_url
from voice_runner.settings import (
    WorkerSettings,
    lease_ttl_seconds,
    resolved_public_base_url,
)
from voice_runner.twilio_voice import hangup_call
from voice_runner.worker import worker_loop

logger = logging.getLogger(__name__)


async def _renew_lease(
    *,
    job_id: uuid.UUID,
    stop: asyncio.Event,
    ttl_seconds: int,
    renew_every: float,
) -> None:
    while True:
        try:
            await asyncio.wait_for(stop.wait(), timeout=renew_every)
            return
        except TimeoutError:
            pass

        try:
            with Session(engine) as session:
                job = crud.get_voice_simulation_job(session=session, job_id=job_id)
                if job is None or job.status != VoiceSimulationJobStatus.CALLING:
                    return

                next_expiry = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
                crud.update_voice_simulation_job(
                    session=session,
                    db_job=job,
                    job_in=VoiceSimulationJobUpdate(
                        lease_expires_at=next_expiry,
                    ),
                )
        except Exception:
            logger.exception("Failed to extend lease job=%s", job_id)


def _fail_job(job_id: uuid.UUID | None, code: str, message: str) -> None:
    if job_id is None:
        return
    try:
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
    except Exception:
        logger.exception("Failed marking job failed job=%s", job_id)


async def _shutdown_active_call() -> None:
    active = active_calls.get_active_call()
    if active is None:
        return

    sid = connexity_settings.TWILIO_ACCOUNT_SID
    tok = connexity_settings.TWILIO_AUTH_TOKEN
    if sid and tok:
        await hangup_call(
            account_sid=sid,
            auth_token=tok,
            call_sid=active.call_sid,
        )
    _fail_job(
        active.job_id,
        "worker_shutdown",
        "Voice worker stopped during an active call.",
    )
    active_calls.clear_active_call()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    stop = asyncio.Event()
    ws_settings = WorkerSettings()
    task = asyncio.create_task(worker_loop(stop, ws_settings))
    app.state.voice_worker_stop = stop
    yield
    stop.set()
    await _shutdown_active_call()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Connexity Voice Worker", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/twiml/{job_id}")
async def twiml_xml(job_id: uuid.UUID) -> Response:
    settings = WorkerSettings()
    try:
        pub = resolved_public_base_url(settings)
    except ValueError:
        return Response(
            content=(
                "VOICE_PUBLIC_BASE_URL or VOICE_WORKER_PUBLIC_HOST_SUFFIX with "
                "POD_NAME is required"
            ),
            status_code=503,
        )
    ws_url = media_stream_wss_url(public_base=pub)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        "  <Connect>\n"
        f'    <Stream url="{escape(ws_url)}">\n'
        f'      <Parameter name="job_id" value="{escape(str(job_id))}"/>\n'
        "    </Stream>\n"
        "  </Connect>\n"
        "</Response>\n"
    )
    return Response(content=xml, media_type="application/xml")


@app.websocket("/ws")
async def twilio_media_ws(websocket: WebSocket) -> None:
    offered = websocket.headers.get("sec-websocket-protocol") or ""
    protos = [p.strip() for p in offered.split(",") if p.strip()]
    subproto = "audio.twilio.com" if "audio.twilio.com" in protos else None
    await websocket.accept(subprotocol=subproto)

    start_payload: dict[str, object] = {}
    parsed_job_id: uuid.UUID | None = None

    renewal: asyncio.Task[None] | None = None
    stop_signal = asyncio.Event()

    ws_settings = WorkerSettings()
    call_failed = False

    try:
        while True:
            message = await websocket.receive()
            if "text" not in message:
                continue
            handshake = json.loads(message["text"])
            if handshake.get("event") == "start":
                start_payload = handshake
                break

        start_inner = cast(dict[str, Any], start_payload["start"])
        bound_call_sid = str(start_inner.get("callSid") or "")
        stream_sid = str(start_inner.get("streamSid") or "")

        raw_params = cast(dict[str, Any], start_inner.get("customParameters") or {})
        job_token = raw_params.get("job_id") or ""
        parsed_job_id = uuid.UUID(str(job_token))

        if active_calls.EXPECTED_JOB_ID != parsed_job_id:
            logger.warning(
                "/ws rejected job=%s expected=%s",
                parsed_job_id,
                active_calls.EXPECTED_JOB_ID,
            )
            await websocket.close(code=4403)
            return

        with Session(engine) as session:
            job = crud.get_voice_simulation_job(session=session, job_id=parsed_job_id)
            if job is None:
                await websocket.close(code=4404)
                return
            if job.status not in (
                VoiceSimulationJobStatus.CLAIMED,
                VoiceSimulationJobStatus.CALLING,
            ):
                await websocket.close(code=4409)
                return

            run_row = session.get(Run, job.run_id)
            case_row = session.get(TestCase, job.test_case_id)
            if run_row is None or run_row.config is None or case_row is None:
                logger.error("Missing Run/TestCase for voice job=%s", parsed_job_id)
                await websocket.close(code=4500)
                return

            crud.update_voice_simulation_job(
                session=session,
                db_job=job,
                job_in=VoiceSimulationJobUpdate(
                    status=VoiceSimulationJobStatus.CALLING,
                    call_started_at=datetime.now(UTC),
                ),
            )

            resolved_run_config = RunConfig.model_validate(run_row.config)
            job_snapshot = VoiceSimulationJob.model_validate(job.model_dump())

        active_calls.STREAM_REGISTRY.notify(parsed_job_id)

        lease_ttl = lease_ttl_seconds(
            max_call_duration_seconds=job_snapshot.max_call_duration_seconds,
            settings=ws_settings,
        )

        renewal = asyncio.create_task(
            _renew_lease(
                job_id=parsed_job_id,
                stop=stop_signal,
                ttl_seconds=lease_ttl,
                renew_every=float(ws_settings.VOICE_WORKER_LEASE_RENEW_SECONDS),
            ),
        )

        await asyncio.wait_for(
            run_pipecat_voice_call(
                websocket=websocket,
                stream_sid=stream_sid,
                call_sid=bound_call_sid,
                job=job_snapshot,
                test_case=case_row,
                run_config=resolved_run_config,
                worker_settings=ws_settings,
            ),
            timeout=float(job_snapshot.max_call_duration_seconds),
        )

    except TimeoutError:
        logger.warning("Call hit max_call_duration_seconds job=%s", parsed_job_id)
        call_failed = True
        _fail_job(parsed_job_id, "call_timeout", "max_call_duration_seconds exceeded")

        sid = connexity_settings.TWILIO_ACCOUNT_SID
        tok = connexity_settings.TWILIO_AUTH_TOKEN
        if bound_call_sid and sid and tok:
            await hangup_call(account_sid=sid, auth_token=tok, call_sid=bound_call_sid)
    except Exception as exc:
        logger.exception("Voice session crashed job=%s", parsed_job_id)
        call_failed = True
        _fail_job(parsed_job_id, "voice_session_error", str(exc))

        sid = connexity_settings.TWILIO_ACCOUNT_SID
        tok = connexity_settings.TWILIO_AUTH_TOKEN
        if bound_call_sid and sid and tok:
            await hangup_call(
                account_sid=sid,
                auth_token=tok,
                call_sid=bound_call_sid,
            )

    finally:
        stop_signal.set()
        if renewal is not None:
            renewal.cancel()
            with suppress(asyncio.CancelledError):
                await renewal

        if parsed_job_id is not None:
            if not call_failed:
                with Session(engine) as session:
                    current = crud.get_voice_simulation_job(
                        session=session, job_id=parsed_job_id
                    )
                    if (
                        current is not None
                        and current.status == VoiceSimulationJobStatus.CALLING
                    ):
                        crud.update_voice_simulation_job(
                            session=session,
                            db_job=current,
                            job_in=VoiceSimulationJobUpdate(
                                status=VoiceSimulationJobStatus.WAITING_FOR_RESULT,
                                call_ended_at=datetime.now(UTC),
                                lease_expires_at=None,
                            ),
                        )

            active_calls.CALL_COMPLETION.resolve(parsed_job_id, None)
