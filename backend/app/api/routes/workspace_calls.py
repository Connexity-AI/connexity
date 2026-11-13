"""The Calls page: the open workspace's calls, newest first, searchable and filtered."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.crud.call_list import CallFilters
from app.models.call_list import CallListPublic
from app.models.enums import CallCheckStatus
from app.services.call_list import workspace_calls

router = APIRouter(tags=["calls"], dependencies=[Depends(get_current_user)])


@router.get("/calls", response_model=CallListPublic)
def list_calls(
    session: SessionDep,
    company_id: CurrentCompany,
    period: Literal["7d", "30d", "90d"] = "30d",
    agent_id: uuid.UUID | None = None,
    result: CallCheckStatus | None = None,
    category: str | None = Query(default=None, max_length=64),
    q: str | None = Query(default=None, max_length=255),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> CallListPublic:
    """The workspace's calls in the period, newest first, with tiles for the period.

    ``q`` is a phone number (its last digits match the end of the caller's number) or a
    call id (Connexity's or the platform's). Callers are shown as their last four digits.
    """
    return workspace_calls(
        session=session,
        company_id=company_id,
        filters=CallFilters(
            period=period, agent_id=agent_id, result=result, category=category, query=q
        ),
        offset=skip,
        limit=limit,
    )
