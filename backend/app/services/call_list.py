"""Turn the calls query into what the Calls page and `list_calls` answer."""

import uuid

from sqlmodel import Session, col, select

from app import crud
from app.crud.call_list import CallFilters, CallRow
from app.models.agent import Agent
from app.models.call_list import (
    CallFilterOption,
    CallListItemPublic,
    CallListPublic,
    CallTilesPublic,
    WorstFindingPublic,
)
from app.models.enums import CheckKind
from app.services.checks.registry import get_check


def _item(row: CallRow) -> CallListItemPublic:
    call = row.call
    duration = None
    if call.ended_at is not None:
        duration = max(0, int((call.ended_at - call.started_at).total_seconds()))
    worst = None
    if row.worst is not None:
        check = get_check(row.worst.check_type)
        worst = WorstFindingPublic(
            title=check.title if check else row.worst.check_type,
            key=row.worst.key,
            category=row.worst.category,
            severity="critical" if row.worst.critical else "warning",
            found_by="rule"
            if check is None or check.kind is CheckKind.RULE
            else "model",
        )
    return CallListItemPublic(
        id=call.id,
        started_at=call.started_at,
        agent_id=call.agent_id,
        agent_name=row.agent_name,
        caller_last_four=crud.caller_last_four(call.caller_number),
        duration_seconds=duration,
        result=row.result,
        worst_finding=worst,
    )


def workspace_calls(
    *,
    session: Session,
    company_id: uuid.UUID,
    filters: CallFilters,
    offset: int,
    limit: int,
) -> CallListPublic:
    rows, has_more = crud.list_workspace_calls(
        session=session,
        company_id=company_id,
        filters=filters,
        offset=offset,
        limit=limit,
    )
    tiles = crud.workspace_call_tiles(
        session=session, company_id=company_id, filters=filters
    )
    agents = session.exec(
        select(Agent)
        .where(
            Agent.company_id == company_id,
            col(Agent.integration_id).is_not(None),
            col(Agent.platform_agent_id).is_not(None),
        )
        .order_by(col(Agent.name))
    ).all()
    return CallListPublic(
        data=[_item(row) for row in rows],
        tiles=CallTilesPublic(**tiles._asdict()),
        has_more=has_more,
        period=filters.period,
        agents=[CallFilterOption(value=str(a.id), label=a.name) for a in agents],
        categories=[
            CallFilterOption(value=c.key, label=c.name)
            for c in crud.list_categories(session=session)
        ],
    )
