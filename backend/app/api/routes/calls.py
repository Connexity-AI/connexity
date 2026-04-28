import logging
import uuid
from datetime import UTC, datetime, timedelta

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

# Retell returns at most _RETELL_PAGE_SIZE per request; when a page comes back
# full we keep paging forward until the backlog is exhausted or we hit the cap.
_RETELL_PAGE_SIZE = 100
_MAX_FETCH_ITERATIONS = 20

# Stale-while-revalidate window for the GET /calls endpoint. Pagination,
# filtering, and React Query refetches inside this window all serve from DB
# without touching Retell; outside it, the next GET schedules one background
# sync. Doubles as a backoff after a failed sync (we don't reset the stamp).
_SYNC_TTL = timedelta(seconds=15)


async def _fetch_and_store_from_retell(
    *,
    session,
    agent,
    incremental: bool,
) -> int:
    """Pull calls from Retell into the DB across every Retell environment on the agent.

    Returns total number of newly-inserted rows.
    """
    environments = crud.list_environments_by_agent(session=session, agent_id=agent.id)
    retell_envs = [
        (env, _integration_name)
        for env, _integration_name in environments
        if env.platform == Platform.RETELL
    ]
    if not retell_envs:
        raise HTTPException(
            status_code=400,
            detail="Add a Retell environment on the Deploy tab first",
        )

    initial_start_after: datetime | None = None
    if incremental:
        initial_start_after = crud.get_latest_call_started_at(
            session=session, agent_id=agent.id
        )

    created_total = 0
    for env, _ in retell_envs:
        integration = crud.get_integration(
            session=session,
            integration_id=env.integration_id,
        )
        if integration is None:
            continue
        api_key = decrypt(integration.encrypted_api_key)

        start_after = initial_start_after
        for _ in range(_MAX_FETCH_ITERATIONS):
            batch = await list_retell_calls(
                api_key,
                agent_id=env.platform_agent_id,
                start_after=start_after,
                limit=_RETELL_PAGE_SIZE,
            )
            if not batch:
                break
            created_total += crud.upsert_calls_from_retell(
                session=session,
                agent_id=agent.id,
                integration_id=integration.id,
                retell_calls=batch,
            )
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
    return created_total


def _is_sync_stale(last_synced_at: datetime | None) -> bool:
    if last_synced_at is None:
        return True
    # The DB column is timezone-naive (sa.DateTime()) and we always write UTC,
    # so treat naive reads as UTC for comparison with datetime.now(UTC).
    last = (
        last_synced_at.replace(tzinfo=UTC)
        if last_synced_at.tzinfo is None
        else last_synced_at
    )
    return (datetime.now(UTC) - last) >= _SYNC_TTL


async def _sync_calls_in_background(agent_id: uuid.UUID) -> None:
    """Run a Retell sync in a fresh DB session after the request response is sent.

    Errors are logged, never raised — there is no caller left to receive them.
    The TTL stamp is set by the caller before scheduling; we do not reset it on
    failure, so failures back off naturally for one ``_SYNC_TTL`` window.
    """
    with Session(engine) as session:
        agent = session.get(Agent, agent_id)
        if agent is None:
            return
        try:
            await _fetch_and_store_from_retell(
                session=session, agent=agent, incremental=True
            )
        except HTTPException as exc:
            logger.warning(
                "background Retell sync for agent %s failed: %s", agent_id, exc.detail
            )
        except Exception:
            logger.exception(
                "unexpected error during background Retell sync for %s", agent_id
            )


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
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Stale-while-revalidate: always serve DB rows; outside _SYNC_TTL, schedule
    # a background sync whose results land in time for the next refetch. Stamp
    # the timestamp now (before scheduling) so concurrent in-window requests
    # see a fresh marker and skip queueing duplicate syncs.
    if _is_sync_stale(agent.calls_last_synced_at):
        crud.touch_calls_last_synced_at(session=session, agent_id=agent_id)
        background_tasks.add_task(_sync_calls_in_background, agent_id)

    items, count = crud.list_calls_for_agent(
        session=session,
        agent_id=agent_id,
        skip=skip,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
    )
    return CallsPublic(data=items, count=count)


@router.post("/agents/{agent_id}/calls/refresh", response_model=CallRefreshResult)
async def refresh_agent_calls(
    session: SessionDep,
    agent_id: uuid.UUID,
) -> CallRefreshResult:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    created = await _fetch_and_store_from_retell(
        session=session, agent=agent, incremental=True
    )
    crud.touch_calls_last_synced_at(session=session, agent_id=agent_id)
    total = crud.count_calls_for_agent(session=session, agent_id=agent_id)
    return CallRefreshResult(created=created, total=total)


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
