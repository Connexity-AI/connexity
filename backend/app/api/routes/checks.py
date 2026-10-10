"""What each check does for an agent, and the record of every change to that."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentCompany, CurrentUser, SessionDep, get_current_user
from app.models import (
    AgentCheckPublic,
    CheckModeUpdate,
    DecisionRecord,
    DecisionRecordPublic,
)
from app.models.enums import DecisionKind
from app.services.checks.base import RuleCheck
from app.services.checks.engine import current_mode, is_loosening
from app.services.checks.registry import CHECKS, get_check

router = APIRouter(
    prefix="/agents/{agent_id}",
    tags=["checks"],
    dependencies=[Depends(get_current_user)],
)


def _require_agent(
    session: SessionDep, company_id: uuid.UUID, agent_id: uuid.UUID
) -> None:
    if (
        crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
        is None
    ):
        raise HTTPException(status_code=404, detail="Agent not found")


def _public(check: RuleCheck, records: list[DecisionRecord]) -> AgentCheckPublic:
    return AgentCheckPublic(
        type=check.type,
        title=check.title,
        description=check.description,
        kind=check.kind,
        version=check.version,
        default_mode=check.default_mode,
        mode=current_mode(check, records),
    )


@router.get("/checks", response_model=list[AgentCheckPublic])
def list_agent_checks(
    session: SessionDep, company_id: CurrentCompany, agent_id: uuid.UUID
) -> list[AgentCheckPublic]:
    """Every check, with what it does for this agent now."""
    _require_agent(session, company_id, agent_id)
    history = crud.check_setting_history(session=session, agent_id=agent_id)
    return [_public(check, history.get(check.type, [])) for check in CHECKS]


@router.put("/checks/{check_type}", response_model=AgentCheckPublic)
def set_agent_check_mode(
    session: SessionDep,
    company_id: CurrentCompany,
    current_user: CurrentUser,
    agent_id: uuid.UUID,
    check_type: str,
    body: CheckModeUpdate,
) -> AgentCheckPublic:
    """Set a check to off, flags or fails for this agent.

    The change is kept as a decision record and applies to calls that start from now
    on; calls already checked keep what they counted for. A reason is required when the
    change loosens the check.
    """
    _require_agent(session, company_id, agent_id)
    check = get_check(check_type)
    if check is None:
        raise HTTPException(status_code=404, detail="No check of this type")
    reason = (body.reason or "").strip() or None

    crud.lock_agent(session=session, agent_id=agent_id)
    records = crud.check_setting_history(session=session, agent_id=agent_id).get(
        check.type, []
    )
    old = current_mode(check, records)
    if body.mode == old:
        session.rollback()
        return _public(check, records)
    if is_loosening(old, body.mode) and reason is None:
        session.rollback()
        raise HTTPException(
            status_code=422,
            detail=(
                f"A reason is required to change this check from '{old.value}' to "
                f"'{body.mode.value}', because it can only improve the numbers"
            ),
        )
    record = crud.record_decision(
        session=session,
        agent_id=agent_id,
        company_id=company_id,
        kind=DecisionKind.CHECK_SETTING,
        subject=check.type,
        old_value=old.value,
        new_value=body.mode.value,
        reason=reason,
        decided_by=current_user,
    )
    return _public(check, [*records, record])


@router.get("/decisions", response_model=list[DecisionRecordPublic])
def list_agent_decisions(
    session: SessionDep,
    company_id: CurrentCompany,
    agent_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[DecisionRecordPublic]:
    """The agent's decision records, newest first."""
    _require_agent(session, company_id, agent_id)
    return [
        DecisionRecordPublic.model_validate(record, from_attributes=True)
        for record in crud.list_decision_records(
            session=session, agent_id=agent_id, limit=limit
        )
    ]
