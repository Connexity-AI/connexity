"""Issues: all findings with the same symptom on one agent."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentCompany, CurrentUser, SessionDep, get_current_user
from app.crud.check import IssueSummary
from app.models import (
    Category,
    CategoryPublic,
    IssuePublic,
    IssueStateUpdate,
)
from app.models.enums import IssueState
from app.models.issue_list import IssueListPublic, IssuePeriod, IssueStatusFilter
from app.models.issue_page import IssuePagePublic
from app.services.checks.registry import get_check
from app.services.issue_list import IssueFilters, workspace_issues
from app.services.issue_page import issue_page

router = APIRouter(tags=["issues"], dependencies=[Depends(get_current_user)])


def _public(
    summary: IssueSummary, categories: dict[uuid.UUID, Category]
) -> IssuePublic:
    issue = summary.issue
    category = categories[issue.category_id]
    check = get_check(issue.check_type)
    return IssuePublic(
        id=issue.id,
        agent_id=issue.agent_id,
        check_type=issue.check_type,
        title=check.title if check else "",
        category=CategoryPublic(
            key=category.key,
            name=category.name,
            position=category.position,
            kind=category.kind,
        ),
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


@router.get("/issues", response_model=IssueListPublic)
def list_issues(
    session: SessionDep,
    company_id: CurrentCompany,
    period: IssuePeriod = "30d",
    agent_id: uuid.UUID | None = None,
    category: str | None = Query(default=None, max_length=64),
    severity: Literal["critical", "warning"] | None = None,
    status: IssueStatusFilter = "open",
    q: str | None = Query(default=None, max_length=255),
) -> IssueListPublic:
    """The Issues page: the open workspace's issues grouped by category, worst first.

    The tiles follow the agent and the period only. ``q`` matches words in an issue's
    title, or its whole id.
    """
    page, _ = workspace_issues(
        session=session,
        company_id=company_id,
        filters=IssueFilters(
            period=period,
            agent_id=agent_id,
            category=category,
            severity=severity,
            status=status,
            query=q,
        ),
    )
    return page


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
    categories = crud.categories_by_id(session=session)
    return [
        _public(summary, categories)
        for summary in crud.list_issues(session=session, agent_id=agent_id)
    ]


@router.get("/issues/{issue_id}", response_model=IssuePagePublic)
def get_issue(
    session: SessionDep, company_id: CurrentCompany, issue_id: uuid.UUID
) -> IssuePagePublic:
    """One issue's page: tiles, the chain, affected calls per day with marks, the latest
    affected calls with their moment, and history. The last 30 days."""
    issue = crud.get_issue(session=session, issue_id=issue_id, company_id=company_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue_page(
        session=session,
        issue=issue,
        summary=crud.summarise_issue(session=session, issue=issue),
    )


@router.put("/issues/{issue_id}/state", response_model=IssuePublic)
def set_issue_state(
    session: SessionDep,
    company_id: CurrentCompany,
    current_user: CurrentUser,
    issue_id: uuid.UUID,
    body: IssueStateUpdate,
) -> IssuePublic:
    """Resolve an issue, archive it, or open it again.

    Kept as a decision record. Archiving requires a reason and takes a duration: until
    it spikes (the default) or forever. "Reopened" is not
    something a person sets: it happens when a resolved issue is found again on a call
    that started after the resolution.
    """
    issue = crud.get_issue(session=session, issue_id=issue_id, company_id=company_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    if body.state is IssueState.REOPENED:
        raise HTTPException(
            status_code=422,
            detail="An issue is set to open, resolved or archived, not to reopened",
        )
    reason = (body.reason or "").strip() or None
    if body.state is IssueState.ARCHIVED and reason is None:
        raise HTTPException(
            status_code=422, detail="A reason is required to archive an issue"
        )
    issue = crud.set_issue_state(
        session=session,
        issue_id=issue.id,
        state=body.state,
        version=(body.version or "").strip() or None,
        reason=reason,
        decided_by=current_user,
        until_spike=body.duration != "forever",
    )
    return _public(
        crud.summarise_issue(session=session, issue=issue),
        crud.categories_by_id(session=session),
    )
