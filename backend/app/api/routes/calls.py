import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlmodel import Session

from app import crud
from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.core.db import engine
from app.models import (
    Call,
    CallLabelUpdate,
    CallPublic,
    CallRefreshResult,
    CallsPublic,
    CallTracePublic,
    Message,
)
from app.models.agent import Agent
from app.services.call_sync import emit, sync_agent_calls
from app.services.trace_capabilities import derive_capabilities

logger = logging.getLogger(__name__)

router = APIRouter(tags=["calls"], dependencies=[Depends(get_current_user)])

_SYNC_TTL = timedelta(seconds=15)


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
    """Run a call sync in a fresh DB session after the response is sent.

    Errors are logged, never raised: there is no caller left to receive them.
    """
    with Session(engine) as session:
        agent = session.get(Agent, agent_id)
        if agent is None:
            return
        try:
            await sync_agent_calls(session=session, agent=agent, incremental=True)
        except HTTPException as exc:
            # Expected for an agent with no provider link; already logged by the sync.
            logger.info("[bg-sync] agent=%s skipped: %s", agent_id, exc.detail)
        except Exception:  # noqa: BLE001 - a background task has no one to raise to
            logger.exception("[bg-sync] agent=%s unexpected error", agent_id)


def _call_or_404(
    *, session: Session, call_id: uuid.UUID, company_id: uuid.UUID
) -> Call:
    call = crud.get_call(session=session, call_id=call_id, company_id=company_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


def _to_public(session: Session, call: Call) -> CallPublic:
    return crud.call_to_public(
        call,
        test_case_count=crud.count_test_cases_for_call(
            session=session, call_id=call.id
        ),
    )


@router.get("/agents/{agent_id}/calls", response_model=CallsPublic)
async def list_agent_calls(
    session: SessionDep,
    background_tasks: BackgroundTasks,
    company_id: CurrentCompany,
    agent_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=200),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> CallsPublic:
    agent = crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    stale = _is_sync_stale(agent.calls_last_synced_at)
    if stale:
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
    emit(
        "list_calls",
        agent_id=str(agent_id),
        rows_returned=len(items),
        total_count=count,
        scheduled_bg_sync=stale,
    )
    return CallsPublic(data=items, count=count)


@router.post("/agents/{agent_id}/calls/refresh", response_model=CallRefreshResult)
async def refresh_agent_calls(
    session: SessionDep,
    company_id: CurrentCompany,
    agent_id: uuid.UUID,
) -> CallRefreshResult:
    agent = crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    created = await sync_agent_calls(session=session, agent=agent, incremental=True)
    crud.touch_calls_last_synced_at(session=session, agent_id=agent_id)
    total = crud.count_calls_for_agent(session=session, agent_id=agent_id)
    return CallRefreshResult(created=created, total=total)


@router.post("/calls/{call_id}/seen", response_model=Message)
def mark_call_seen_endpoint(
    session: SessionDep,
    company_id: CurrentCompany,
    call_id: uuid.UUID,
) -> Message:
    _call_or_404(session=session, call_id=call_id, company_id=company_id)
    crud.mark_call_seen(session=session, call_id=call_id)
    return Message(message="ok")


@router.patch("/calls/{call_id}/label", response_model=CallPublic)
def set_call_label_endpoint(
    session: SessionDep,
    company_id: CurrentCompany,
    call_id: uuid.UUID,
    body: CallLabelUpdate,
) -> CallPublic:
    # Verify ownership first via get_call (scoped by company)
    _call_or_404(session=session, call_id=call_id, company_id=company_id)
    call = crud.set_call_label(session=session, call_id=call_id, label=body.label)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return _to_public(session, call)


@router.get("/calls/{call_id}", response_model=CallPublic)
def get_call_detail(
    session: SessionDep,
    company_id: CurrentCompany,
    call_id: uuid.UUID,
) -> CallPublic:
    call = _call_or_404(session=session, call_id=call_id, company_id=company_id)
    return _to_public(session, call)


@router.get("/calls/{call_id}/trace", response_model=CallTracePublic)
def get_call_trace(
    session: SessionDep,
    company_id: CurrentCompany,
    call_id: uuid.UUID,
) -> CallTracePublic:
    """The call's trace, with what it can support.

    404 with "not converted" when the call was synced but has no trace yet.
    """
    call = _call_or_404(session=session, call_id=call_id, company_id=company_id)
    trace = crud.get_trace(session=session, call=call)
    if trace is None:
        raise HTTPException(
            status_code=404, detail="This call has not been converted to a trace yet"
        )
    return CallTracePublic(trace=trace, capabilities=derive_capabilities(trace))
