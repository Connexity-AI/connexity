"""Issues: all findings with the same symptom on one agent."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app import crud
from app.api.deps import CurrentCompany, CurrentUser, SessionDep, get_current_user
from app.crud.check import IssueSummary
from app.models import (
    IssueDetailPublic,
    IssueFindingPublic,
    IssuePublic,
    IssueStateUpdate,
)
from app.models.enums import IssueState
from app.services.checks.registry import get_check

router = APIRouter(tags=["issues"], dependencies=[Depends(get_current_user)])

_MAX_FINDINGS = 200


def _public(summary: IssueSummary) -> IssuePublic:
    issue = summary.issue
    check = get_check(issue.check_type)
    return IssuePublic(
        id=issue.id,
        agent_id=issue.agent_id,
        check_type=issue.check_type,
        title=check.title if check else "",
        key=issue.key or None,
        state=issue.state,
        resolved_at=issue.resolved_at,
        resolved_version=issue.resolved_version,
        finding_count=summary.finding_count,
        call_count=summary.call_count,
        first_seen_at=summary.first_seen_at,
        last_seen_at=summary.last_seen_at,
        created_at=issue.created_at,
    )


@router.get("/agents/{agent_id}/issues", response_model=list[IssuePublic])
def list_agent_issues(
    session: SessionDep, company_id: CurrentCompany, agent_id: uuid.UUID
) -> list[IssuePublic]:
    """The agent's issues, the one seen most recently first."""
    if (
        crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
        is None
    ):
        raise HTTPException(status_code=404, detail="Agent not found")
    return [
        _public(summary)
        for summary in crud.list_issues(session=session, agent_id=agent_id)
    ]


@router.get("/issues/{issue_id}", response_model=IssueDetailPublic)
def get_issue(
    session: SessionDep, company_id: CurrentCompany, issue_id: uuid.UUID
) -> IssueDetailPublic:
    """One issue with its findings and the calls they are on."""
    issue = crud.get_issue(session=session, issue_id=issue_id, company_id=company_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    summary = _public(crud.summarise_issue(session=session, issue=issue))
    return IssueDetailPublic(
        **summary.model_dump(),
        findings=[
            IssueFindingPublic(
                id=finding.id,
                call_id=finding.call_id,
                call_started_at=started,
                check_version=finding.check_version,
                event_ids=finding.event_keys,
                detail=finding.detail,
                effect=finding.effect,
                retroactive=finding.retroactive,
            )
            for finding, started in crud.list_issue_findings(
                session=session, issue_id=issue.id, limit=_MAX_FINDINGS
            )
        ],
    )


@router.put("/issues/{issue_id}/state", response_model=IssuePublic)
def set_issue_state(
    session: SessionDep,
    company_id: CurrentCompany,
    current_user: CurrentUser,
    issue_id: uuid.UUID,
    body: IssueStateUpdate,
) -> IssuePublic:
    """Resolve an issue, accept it as known, or reopen it.

    Kept as a decision record. Accepting requires a reason. "Regressed" is not
    something a person sets: it happens when a resolved issue is found again on a call
    that started after the resolution.
    """
    issue = crud.get_issue(session=session, issue_id=issue_id, company_id=company_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    if body.state is IssueState.REGRESSED:
        raise HTTPException(
            status_code=422,
            detail="An issue is set to open, resolved or accepted, not to regressed",
        )
    reason = (body.reason or "").strip() or None
    if body.state is IssueState.ACCEPTED and reason is None:
        raise HTTPException(
            status_code=422, detail="A reason is required to accept an issue as known"
        )
    issue = crud.set_issue_state(
        session=session,
        issue_id=issue.id,
        state=body.state,
        version=(body.version or "").strip() or None,
        reason=reason,
        decided_by=current_user,
    )
    return _public(crud.summarise_issue(session=session, issue=issue))
