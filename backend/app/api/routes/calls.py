import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.core.db import engine
from app.core.encryption import decrypt
from app.models import (
    CallPublic,
    CallRefreshResult,
    CallsPublic,
    Message,
)
from app.models.agent import Agent
from app.models.enums import Platform
from app.models.test_case import TestCase
from app.services.retell import list_retell_calls

logger = logging.getLogger(__name__)

router = APIRouter(tags=["calls"], dependencies=[Depends(get_current_user)])

_RETELL_PAGE_SIZE = 100
_MAX_FETCH_ITERATIONS = 20

_SYNC_TTL = timedelta(seconds=15)


def _emit(event: str, **fields: Any) -> None:
    """Emit a single wide-event log line as JSON for Cloud Logging to ingest."""
    payload = {"event": event, **fields}
    logger.warning(json.dumps(payload, default=str))


async def _fetch_and_store_from_retell(
    *,
    session,
    agent,
    incremental: bool,
) -> int:
    """Pull calls from Retell into the DB across every Retell environment on the agent.

    Returns total number of newly-inserted rows.
    """
    started = time.monotonic()
    event: dict[str, Any] = {
        "agent_id": str(agent.id),
        "incremental": incremental,
        "envs_total": 0,
        "retell_envs": 0,
        "envs": [],
        "created_total": 0,
        "status": "ok",
    }
    try:
        environments = crud.list_environments_by_agent(
            session=session, agent_id=agent.id
        )
        retell_envs = [
            (env, name) for env, name in environments if env.platform == Platform.RETELL
        ]
        event["envs_total"] = len(environments)
        event["retell_envs"] = len(retell_envs)

        if not retell_envs:
            event["status"] = "no_retell_env"
            raise HTTPException(
                status_code=400,
                detail="Add a Retell environment on the Deploy tab first",
            )

        created_total = 0
        for env, _ in retell_envs:
            env_event: dict[str, Any] = {
                "env_id": str(env.id),
                "platform_agent_id": env.platform_agent_id,
                "integration_id": str(env.integration_id)
                if env.integration_id
                else None,
                "iterations": 0,
                "fetched": 0,
                "inserted": 0,
                "skipped_dupes": 0,
                "start_after": None,
                "status": "ok",
            }
            event["envs"].append(env_event)

            integration = crud.get_integration(
                session=session,
                integration_id=env.integration_id,
            )
            if integration is None:
                env_event["status"] = "missing_integration"
                continue
            try:
                api_key = decrypt(integration.encrypted_api_key)
            except Exception as exc:
                env_event["status"] = "decrypt_failed"
                env_event["error"] = repr(exc)
                raise
            env_event["api_key_len"] = len(api_key) if api_key else 0

            # Per-environment watermark: the latest started_at of calls already
            # stored for this (agent, retell_agent_id) pair. A brand-new env on
            # an agent that has prior calls from a different env still gets a
            # full backfill instead of inheriting the other env's cutoff.
            start_after: datetime | None = None
            if incremental:
                start_after = crud.get_latest_call_started_at(
                    session=session,
                    agent_id=agent.id,
                    retell_agent_id=env.platform_agent_id,
                )
            env_event["start_after"] = start_after
            for iteration in range(_MAX_FETCH_ITERATIONS):
                env_event["iterations"] = iteration + 1
                try:
                    batch = await list_retell_calls(
                        api_key,
                        agent_id=env.platform_agent_id,
                        start_after=start_after,
                        limit=_RETELL_PAGE_SIZE,
                    )
                except HTTPException as exc:
                    env_event["status"] = "retell_error"
                    env_event["error"] = f"{exc.status_code}: {exc.detail}"
                    raise
                if not batch:
                    break
                inserted = crud.upsert_calls_from_retell(
                    session=session,
                    agent_id=agent.id,
                    integration_id=integration.id,
                    retell_calls=batch,
                )
                env_event["fetched"] += len(batch)
                env_event["inserted"] += inserted
                env_event["skipped_dupes"] += len(batch) - inserted
                created_total += inserted
                if len(batch) < _RETELL_PAGE_SIZE:
                    break
                newest_ms = max(
                    (c.start_timestamp for c in batch if c.start_timestamp is not None),
                    default=None,
                )
                if newest_ms is None:
                    break
                next_after = datetime.fromtimestamp(newest_ms / 1000, tz=UTC)
                if start_after is not None and next_after <= start_after:
                    break
                start_after = next_after
        event["created_total"] = created_total
        return created_total
    except HTTPException as exc:
        if event["status"] == "ok":
            event["status"] = "http_error"
        event["error"] = f"{exc.status_code}: {exc.detail}"
        raise
    except Exception as exc:
        event["status"] = "unhandled_exception"
        event["error"] = repr(exc)
        raise
    finally:
        event["duration_ms"] = int((time.monotonic() - started) * 1000)
        _emit("retell_sync", **event)


def _is_sync_stale(last_synced_at: datetime | None) -> bool:
    if last_synced_at is None:
        return True
    last = (
        last_synced_at.replace(tzinfo=UTC)
        if last_synced_at.tzinfo is None
        else last_synced_at
    )
    return (datetime.now(UTC) - last) >= _SYNC_TTL


async def _sync_calls_in_background(agent_id: uuid.UUID) -> None:
    """Run a Retell sync in a fresh DB session after the request response is sent.

    Errors are logged, never raised — there is no caller left to receive them.
    """
    started = time.monotonic()
    event: dict[str, Any] = {
        "agent_id": str(agent_id),
        "status": "ok",
    }
    try:
        with Session(engine) as session:
            agent = session.get(Agent, agent_id)
            if agent is None:
                event["status"] = "agent_not_found"
                return
            try:
                created = await _fetch_and_store_from_retell(
                    session=session, agent=agent, incremental=True
                )
                event["created"] = created
            except HTTPException as exc:
                event["status"] = "http_error"
                event["error"] = f"{exc.status_code}: {exc.detail}"
            except Exception as exc:
                event["status"] = "unhandled_exception"
                event["error"] = repr(exc)
                logger.exception("[bg-sync] agent=%s UNEXPECTED ERROR", agent_id)
    finally:
        event["duration_ms"] = int((time.monotonic() - started) * 1000)
        _emit("bg_sync", **event)


@router.get("/agents/{agent_id}/calls", response_model=CallsPublic)
async def list_agent_calls(
    session: SessionDep,
    background_tasks: BackgroundTasks,
    agent_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=200),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> CallsPublic:
    started = time.monotonic()
    event: dict[str, Any] = {
        "agent_id": str(agent_id),
        "skip": skip,
        "limit": limit,
        "date_from": date_from,
        "date_to": date_to,
        "agent_found": False,
        "stale": False,
        "scheduled_bg_sync": False,
        "rows_returned": 0,
        "total_count": 0,
        "status": "ok",
    }
    try:
        agent = crud.get_agent(session=session, agent_id=agent_id)
        if agent is None:
            event["status"] = "agent_not_found"
            raise HTTPException(status_code=404, detail="Agent not found")
        event["agent_found"] = True
        event["last_synced_at"] = agent.calls_last_synced_at

        stale = _is_sync_stale(agent.calls_last_synced_at)
        event["stale"] = stale

        if stale:
            crud.touch_calls_last_synced_at(session=session, agent_id=agent_id)
            background_tasks.add_task(_sync_calls_in_background, agent_id)
            event["scheduled_bg_sync"] = True

        items, count = crud.list_calls_for_agent(
            session=session,
            agent_id=agent_id,
            skip=skip,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )
        event["rows_returned"] = len(items)
        event["total_count"] = count
        return CallsPublic(data=items, count=count)
    except HTTPException as exc:
        if event["status"] == "ok":
            event["status"] = "http_error"
        event["http_status"] = exc.status_code
        event["error"] = str(exc.detail)
        raise
    except Exception as exc:
        event["status"] = "unhandled_exception"
        event["error"] = repr(exc)
        logger.exception("[list-calls] agent=%s UNHANDLED EXCEPTION", agent_id)
        raise
    finally:
        event["duration_ms"] = int((time.monotonic() - started) * 1000)
        _emit("list_calls", **event)


@router.post("/agents/{agent_id}/calls/refresh", response_model=CallRefreshResult)
async def refresh_agent_calls(
    session: SessionDep,
    agent_id: uuid.UUID,
) -> CallRefreshResult:
    started = time.monotonic()
    event: dict[str, Any] = {
        "agent_id": str(agent_id),
        "status": "ok",
        "created": 0,
        "total": 0,
    }
    try:
        agent = crud.get_agent(session=session, agent_id=agent_id)
        if agent is None:
            event["status"] = "agent_not_found"
            raise HTTPException(status_code=404, detail="Agent not found")

        created = await _fetch_and_store_from_retell(
            session=session, agent=agent, incremental=True
        )
        crud.touch_calls_last_synced_at(session=session, agent_id=agent_id)
        total = crud.count_calls_for_agent(session=session, agent_id=agent_id)
        event["created"] = created
        event["total"] = total
        return CallRefreshResult(created=created, total=total)
    except HTTPException as exc:
        if event["status"] == "ok":
            event["status"] = "http_error"
        event["http_status"] = exc.status_code
        event["error"] = str(exc.detail)
        raise
    except Exception as exc:
        event["status"] = "unhandled_exception"
        event["error"] = repr(exc)
        logger.exception("[refresh-calls] agent=%s UNHANDLED EXCEPTION", agent_id)
        raise
    finally:
        event["duration_ms"] = int((time.monotonic() - started) * 1000)
        _emit("refresh_calls", **event)


def _call_or_404(*, session, call_id: uuid.UUID):
    call = crud.get_call(session=session, call_id=call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.post("/calls/{call_id}/seen", response_model=Message)
def mark_call_seen_endpoint(
    session: SessionDep,
    call_id: uuid.UUID,
) -> Message:
    _call_or_404(session=session, call_id=call_id)
    crud.mark_call_seen(session=session, call_id=call_id)
    return Message(message="ok")


@router.get("/calls/{call_id}", response_model=CallPublic)
def get_call_detail(
    session: SessionDep,
    call_id: uuid.UUID,
) -> CallPublic:
    call = _call_or_404(session=session, call_id=call_id)
    is_new = call.seen_at is None
    tc_count = int(
        session.exec(
            select(func.count(TestCase.id)).where(TestCase.source_call_id == call_id)
        ).one()
    )
    return CallPublic(
        id=call.id,
        agent_id=call.agent_id,
        retell_call_id=call.retell_call_id,
        retell_agent_id=call.retell_agent_id,
        started_at=call.started_at,
        duration_seconds=call.duration_seconds,
        status=call.status,
        transcript=call.transcript,
        is_new=is_new,
        test_case_count=tc_count,
        created_at=call.created_at,
    )
