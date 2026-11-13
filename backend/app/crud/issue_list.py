"""The counts the Issues page and `list_issues` need for a period (plan
`plans/2026-11-13-issues-page.md`). Which issues show, and in what order, is decided in
`app/services/issue_list.py`.

Call times are stored naive, in UTC. A deleted call counts for nothing.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import ColumnElement
from sqlmodel import Session, col, func, select

from app.crud.call_list import PERIODS
from app.models.call import Call
from app.models.check import Finding, Issue
from app.models.enums import IssueState

# An issue that is happening: it counts in Open, Critical and Calls affected.
LIVE_STATES = (IssueState.OPEN, IssueState.REOPENED)


def period_start(period: str) -> datetime:
    return datetime.now(UTC) - timedelta(days=PERIODS.get(period, 30))


def _in_period(since: datetime) -> list[ColumnElement[bool]]:
    return [
        col(Call.deleted_at).is_(None),
        col(Call.started_at) >= since.replace(tzinfo=None),
    ]


def calls_affected_by_issue(
    *, session: Session, issue_ids: list[uuid.UUID], since: datetime
) -> dict[uuid.UUID, int]:
    """Distinct calls in the period each issue was found on."""
    if not issue_ids:
        return {}
    rows = session.exec(
        select(Finding.issue_id, func.count(func.distinct(col(Finding.call_id))))
        .join(Call, col(Call.id) == col(Finding.call_id))
        .where(col(Finding.issue_id).in_(issue_ids), *_in_period(since))
        .group_by(col(Finding.issue_id))
    ).all()
    return dict(rows)


def calls_affected_by_category(
    *, session: Session, issue_ids: list[uuid.UUID], since: datetime
) -> dict[uuid.UUID, int]:
    """Distinct calls in the period that any of these issues was found on, per
    category. A call two issues of one category share counts once."""
    if not issue_ids:
        return {}
    rows = session.exec(
        select(Issue.category_id, func.count(func.distinct(col(Finding.call_id))))
        .join(Finding, col(Finding.issue_id) == col(Issue.id))
        .join(Call, col(Call.id) == col(Finding.call_id))
        .where(col(Issue.id).in_(issue_ids), *_in_period(since))
        .group_by(col(Issue.category_id))
    ).all()
    return dict(rows)


def calls_by_agent(
    *, session: Session, company_id: uuid.UUID, since: datetime
) -> dict[uuid.UUID, int]:
    """Each agent's calls in the period."""
    rows = session.exec(
        select(Call.agent_id, func.count())
        .where(Call.company_id == company_id, *_in_period(since))
        .group_by(col(Call.agent_id))
    ).all()
    return dict(rows)


def calls_with_live_issues(
    *,
    session: Session,
    company_id: uuid.UUID,
    since: datetime,
    agent_id: uuid.UUID | None,
) -> int:
    """Distinct calls in the period with a finding from an open or reopened issue."""
    query = (
        select(func.count(func.distinct(col(Finding.call_id))))
        .join(Issue, col(Issue.id) == col(Finding.issue_id))
        .join(Call, col(Call.id) == col(Finding.call_id))
        .where(
            Issue.company_id == company_id,
            col(Issue.state).in_(LIVE_STATES),
            *_in_period(since),
        )
    )
    if agent_id is not None:
        query = query.where(Issue.agent_id == agent_id)
    return session.exec(query).one()
