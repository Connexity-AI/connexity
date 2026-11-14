"""The Issues page and `list_issues`: the workspace's issues for a period, searched,
filtered, grouped by category and worst first (plan `plans/2026-11-13-issues-page.md`).

Which issues a period shows: open and reopened ones always; a resolved one when it was
resolved in the period; an archived one always. Tiles follow the agent and the period
only, never the search or the other filters.
"""

import uuid
from datetime import UTC, datetime
from typing import NamedTuple

from sqlmodel import Session, col, select

from app import crud
from app.crud.check import IssueSummary
from app.crud.issue_list import (
    LIVE_STATES,
    calls_affected_by_category,
    calls_affected_by_issue,
    calls_by_agent,
    calls_with_live_issues,
    period_start,
)
from app.models.agent import Agent
from app.models.call_list import CallFilterOption
from app.models.enums import CheckKind, IssueState
from app.models.issue_list import (
    IssueGroupPublic,
    IssueListItemPublic,
    IssueListPublic,
    IssuePeriod,
    IssueStatusFilter,
    IssueTilesPublic,
)
from app.services.checks.registry import get_check

# Grouping needs every issue at once, so the web answer is not paged; this caps it.
MAX_ISSUES = 500

_STATUS: dict[str, tuple[IssueState, ...]] = {
    "open": LIVE_STATES,
    "reopened": (IssueState.REOPENED,),
    "resolved": (IssueState.RESOLVED,),
    "archived": (IssueState.ARCHIVED,),
}


class IssueFilters(NamedTuple):
    period: IssuePeriod = "30d"
    agent_id: uuid.UUID | None = None
    category: str | None = None  # a category key
    severity: str | None = None  # critical or warning
    status: IssueStatusFilter = "open"
    query: str | None = None


def issue_title(check_type: str, key: str | None) -> str:
    check = get_check(check_type)
    title = check.title if check else check_type
    return f"{title}: {key}" if key else title


def _shows_in_period(summary: IssueSummary, since: datetime) -> bool:
    issue = summary.issue
    if issue.state is IssueState.RESOLVED:
        resolved = issue.resolved_at
        if resolved is None:
            return False
        if resolved.tzinfo is None:
            resolved = resolved.replace(tzinfo=UTC)
        return resolved >= since
    return True


def _matches(item: IssueListItemPublic, query: str) -> bool:
    text = query.strip().lower()
    if not text:
        return True
    return text == str(item.id) or text in item.title.lower()


def _rank(item: IssueListItemPublic) -> tuple[int, int, float]:
    """Worst first: live Critical or Reopened, then other live, then the rest; then by
    calls affected, then the most recently seen."""
    live = item.state in LIVE_STATES
    if live and (item.severity == "critical" or item.state is IssueState.REOPENED):
        tier = 0
    elif live:
        tier = 1
    else:
        tier = 2
    seen = item.last_seen_at.timestamp() if item.last_seen_at else 0.0
    return (tier, -item.calls_affected, -seen)


def workspace_issues(
    *, session: Session, company_id: uuid.UUID, filters: IssueFilters
) -> tuple[IssueListPublic, list[IssueListItemPublic]]:
    """The page's answer, and every matching issue worst first (for `list_issues`)."""
    since = period_start(filters.period)
    summaries = [
        summary
        for summary in crud.list_workspace_issues(
            session=session, company_id=company_id, agent_id=filters.agent_id
        )
        if _shows_in_period(summary, since)
    ]
    issue_ids = [summary.issue.id for summary in summaries]
    affected = calls_affected_by_issue(
        session=session, issue_ids=issue_ids, since=since
    )
    per_agent = calls_by_agent(session=session, company_id=company_id, since=since)
    agents = list(
        session.exec(
            select(Agent)
            .where(Agent.company_id == company_id)
            .order_by(col(Agent.name))
        ).all()
    )
    names = {agent.id: agent.name for agent in agents}
    categories = crud.list_categories(session=session)
    by_id = {category.id: category for category in categories}

    items: list[IssueListItemPublic] = []
    for summary in summaries:
        issue = summary.issue
        check = get_check(issue.check_type)
        kind = check.kind if check else summary.kind
        items.append(
            IssueListItemPublic(
                id=issue.id,
                agent_id=issue.agent_id,
                agent_name=names.get(issue.agent_id, ""),
                title=issue_title(issue.check_type, issue.key or None),
                check_type=issue.check_type,
                key=issue.key or None,
                category=by_id[issue.category_id].key,
                severity="critical" if summary.critical else "warning",
                found_by="rule" if kind in (None, CheckKind.RULE) else "model",
                state=issue.state,
                resolved_version=issue.resolved_version,
                calls_affected=affected.get(issue.id, 0),
                calls_total=per_agent.get(issue.agent_id, 0),
                last_seen_at=summary.last_seen_at,
            )
        )

    live = [item for item in items if item.state in LIVE_STATES]
    tiles = IssueTilesPublic(
        open=len(live),
        critical=sum(1 for item in live if item.severity == "critical"),
        reopened=sum(1 for item in live if item.state is IssueState.REOPENED),
        resolved=sum(1 for item in items if item.state is IssueState.RESOLVED),
        calls_affected=calls_with_live_issues(
            session=session,
            company_id=company_id,
            since=since,
            agent_id=filters.agent_id,
        ),
        calls=per_agent.get(filters.agent_id, 0)
        if filters.agent_id is not None
        else sum(per_agent.values()),
    )

    states = _STATUS[filters.status]
    matching = sorted(
        (
            item
            for item in items
            if item.state in states
            and (filters.category is None or item.category == filters.category)
            and (filters.severity is None or item.severity == filters.severity)
            and (filters.query is None or _matches(item, filters.query))
        ),
        key=_rank,
    )
    # The worst ones when there are too many; grouping keeps their order (a stable sort).
    order = {category.key: category.position for category in categories}
    shown = sorted(matching[:MAX_ISSUES], key=lambda item: order.get(item.category, 0))
    group_calls = calls_affected_by_category(
        session=session, issue_ids=[item.id for item in shown], since=since
    )
    groups: list[IssueGroupPublic] = []
    for category in categories:
        rows = [item for item in shown if item.category == category.key]
        if not rows:
            continue
        groups.append(
            IssueGroupPublic(
                category=CallFilterOption(value=category.key, label=category.name),
                issue_count=len(rows),
                calls_affected=group_calls.get(category.id, 0),
                critical=sum(
                    1
                    for item in rows
                    if item.severity == "critical" and item.state in LIVE_STATES
                ),
                issues=rows,
            )
        )
    page = IssueListPublic(
        tiles=tiles,
        groups=groups,
        total=len(matching),
        truncated=len(matching) > len(shown),
        period=filters.period,
        status=filters.status,
        agents=[
            CallFilterOption(value=str(agent.id), label=agent.name)
            for agent in agents
            if agent.integration_id is not None and agent.platform_agent_id is not None
        ],
        categories=[
            CallFilterOption(value=category.key, label=category.name)
            for category in categories
        ],
    )
    return page, matching
