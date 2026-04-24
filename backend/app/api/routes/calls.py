import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import select

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.core.encryption import decrypt
from app.models import (
    CallPublic,
    CallRefreshResult,
    CallsPublic,
    Message,
)
from app.models.enums import Platform
from app.models.test_case import TestCase
from app.services.retell import list_retell_calls

router = APIRouter(tags=["calls"], dependencies=[Depends(get_current_user)])

# Retell returns at most _RETELL_PAGE_SIZE per request; when a page comes back
# full we keep paging forward until the backlog is exhausted or we hit the cap.
_RETELL_PAGE_SIZE = 100
_MAX_FETCH_ITERATIONS = 20


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
            user_id=agent.created_by,
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


@router.get("/agents/{agent_id}/calls", response_model=CallsPublic)
async def list_agent_calls(
    session: SessionDep,
    current_user: CurrentUser,
    agent_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=200),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> CallsPublic:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if agent is None or agent.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        await _fetch_and_store_from_retell(
            session=session, agent=agent, incremental=True
        )
    except HTTPException:
        # Don't block the page load if the agent has no environment yet or
        # Retell is unreachable — return whatever we already have in DB.
        pass

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
    current_user: CurrentUser,
    agent_id: uuid.UUID,
) -> CallRefreshResult:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if agent is None or agent.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Agent not found")

    created = await _fetch_and_store_from_retell(
        session=session, agent=agent, incremental=True
    )
    total = crud.count_calls_for_agent(session=session, agent_id=agent_id)
    return CallRefreshResult(created=created, total=total)


def _owned_call_or_404(*, session, current_user, call_id: uuid.UUID):
    call = crud.get_call(session=session, call_id=call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    agent = crud.get_agent(session=session, agent_id=call.agent_id)
    if agent is None or agent.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.post("/calls/{call_id}/seen", response_model=Message)
def mark_call_seen_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
    call_id: uuid.UUID,
) -> Message:
    _owned_call_or_404(session=session, current_user=current_user, call_id=call_id)
    crud.mark_call_seen(session=session, call_id=call_id)
    return Message(message="ok")


@router.get("/calls/{call_id}", response_model=CallPublic)
def get_call_detail(
    session: SessionDep,
    current_user: CurrentUser,
    call_id: uuid.UUID,
) -> CallPublic:
    call = _owned_call_or_404(
        session=session, current_user=current_user, call_id=call_id
    )
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
