"""One issue's page and `get_issue` (plan `plans/2026-11-13-issue-page.md`).

Everything covers the last 30 days, as the design's "Last 30 days" label says. The
page counts the issue's own calls even while it is archived: hiding an archived issue
applies to calls, not to its own page.
"""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from app import crud
from app.crud.check import CONNEXITY, IssueSummary
from app.crud.issue_page import (
    agent_calls_since,
    agent_version_starts,
    first_finding_call,
    issue_calls,
    issue_calls_per_day,
    issue_decisions,
    issue_moments,
    period_days,
)
from app.models.agent import Agent
from app.models.call import Call
from app.models.call_list import CallFilterOption, IssueMomentPublic
from app.models.check import DecisionRecord, Issue
from app.models.enums import CallCheckStatus, CheckKind, IssueState
from app.models.issue_page import (
    ArchiveDuration,
    IssueAffectedCallPublic,
    IssueArchivePublic,
    IssueChainPublic,
    IssueDayPublic,
    IssueFixedPublic,
    IssueFoundPublic,
    IssueHistoryPublic,
    IssueMarkPublic,
    IssuePagePublic,
    IssuePageTilesPublic,
)
from app.models.user import User
from app.services.checks.registry import get_check
from app.services.issue_list import issue_title

DAYS = 30
AFFECTED_CALLS = 10


def _duration(record: DecisionRecord) -> ArchiveDuration | None:
    value = (record.detail or {}).get("duration")
    return value if value in ("until_spike", "forever") else None


def _people(session: Session, records: list[DecisionRecord]) -> dict[str, str]:
    """Who each record's person is, by the name they gave or their email's first part."""
    ids = {r.decided_by for r in records if r.decided_by is not None}
    names = {
        user.id: (user.full_name or "").strip() or user.email.split("@")[0]
        for user in session.exec(select(User).where(col(User.id).in_(ids))).all()
    }
    return {
        str(r.id): names.get(r.decided_by, r.decided_by_email.split("@")[0])
        if r.decided_by is not None
        else r.decided_by_email
        for r in records
    }


def _history_line(record: DecisionRecord, by: str) -> IssueHistoryPublic:
    old, new = record.old_value, record.new_value
    connexity = record.decided_by is None and record.decided_by_email == CONNEXITY
    if new == IssueState.ARCHIVED.value:
        kind, what = "archived", "Archived"
    elif old == IssueState.ARCHIVED.value and connexity:
        kind, what = "spiked", "Came back: it spiked"
    elif old == IssueState.ARCHIVED.value:
        kind, what = "unarchived", "Unarchived"
    elif new == IssueState.RESOLVED.value:
        kind, what = "resolved", "Resolved"
    elif new == IssueState.REOPENED.value:
        kind, what = "reopened", "Reopened"
    else:
        kind, what = "changed", f"Set to {new}"
    return IssueHistoryPublic(
        kind=kind,  # type: ignore[arg-type]
        what=what,
        by=None if connexity else by,
        assistant=record.assistant_name,
        at=record.created_at.replace(tzinfo=UTC)
        if record.created_at.tzinfo is None
        else record.created_at,
        reason=record.reason,
        duration=_duration(record),
    )


def issue_page(
    *, session: Session, issue: Issue, summary: IssueSummary
) -> IssuePagePublic:
    now = datetime.now(UTC)
    since = now - timedelta(days=DAYS)
    agent = session.get(Agent, issue.agent_id)
    category = crud.categories_by_id(session=session)[issue.category_id]
    check = get_check(issue.check_type)
    kind = check.kind if check else summary.kind

    records = issue_decisions(session=session, issue=issue)
    people = _people(session, records)
    history = [_history_line(r, people[str(r.id)]) for r in records]

    first = first_finding_call(session=session, issue_id=issue.id)
    found = (
        IssueFoundPublic(
            at=first.started_at.replace(tzinfo=UTC),
            call_id=first.id,
            caller_last_four=crud.caller_last_four(first.caller_number),
        )
        if first is not None
        else None
    )
    if found is not None:
        history.append(
            IssueHistoryPublic(
                kind="opened",
                what="Opened",
                by=None,
                at=found.at,
                reason=f"First seen on call •••• {found.caller_last_four}"
                if found.caller_last_four
                else "First seen",
            )
        )

    archive = None
    if issue.state is IssueState.ARCHIVED:
        last = next((r for r in records if r.new_value == "archived"), None)
        if last is not None:
            archive = IssueArchivePublic(
                by=people[str(last.id)],
                assistant=last.assistant_name,
                at=issue.archived_at or last.created_at,
                duration=_duration(last)
                or ("until_spike" if issue.archive_until_spike else "forever"),
                reason=last.reason,
            )

    per_day = issue_calls_per_day(session=session, issue_id=issue.id, since=since)
    days = [
        IssueDayPublic(day=day, calls=per_day.get(day, 0))
        for day in period_days(since, DAYS)
    ]
    first_day = days[0].day
    marks: list[IssueMarkPublic] = [
        IssueMarkPublic(day=started.date(), kind="version", label=f"Version {version}")
        for version, started in agent_version_starts(
            session=session, agent_id=issue.agent_id
        )[1:]  # the first version is where the agent started, not a change
        if started.date() >= first_day
    ]
    for line in reversed(history):  # oldest first, so same-day marks keep order
        if line.at.date() < first_day:
            continue
        if line.kind == "archived":
            who = "your assistant" if line.assistant else line.by
            marks.append(
                IssueMarkPublic(
                    day=line.at.date(), kind="archived", label=f"Archived by {who}"
                )
            )
        elif line.kind == "spiked":
            marks.append(
                IssueMarkPublic(day=line.at.date(), kind="spiked", label="Spiked")
            )
    marks.sort(key=lambda m: m.day)

    calls = issue_calls(
        session=session, issue_id=issue.id, since=since, limit=AFFECTED_CALLS
    )
    moments = issue_moments(
        session=session, issue_id=issue.id, call_ids=[c.id for c in calls]
    )
    results = crud.call_check_statuses(session=session, call_ids=[c.id for c in calls])

    def duration(call: Call) -> int | None:
        if call.ended_at is None:
            return None
        return max(0, int((call.ended_at - call.started_at).total_seconds()))

    return IssuePagePublic(
        id=issue.id,
        title=issue_title(issue.check_type, issue.key or None),
        check_type=issue.check_type,
        key=issue.key or None,
        agent_id=issue.agent_id,
        agent_name=agent.name if agent else "",
        category=CallFilterOption(value=category.key, label=category.name),
        severity="critical" if summary.critical else "warning",
        found_by="rule" if kind in (None, CheckKind.RULE) else "model",
        state=issue.state,
        resolved_version=issue.resolved_version,
        archive=archive,
        tiles=IssuePageTilesPublic(
            calls_affected=sum(d.calls for d in days),
            calls_total=agent_calls_since(
                session=session, agent_id=issue.agent_id, since=since
            ),
            first_seen_at=summary.first_seen_at,
            last_seen_at=summary.last_seen_at,
        ),
        chain=IssueChainPublic(
            found=found,
            fixed=IssueFixedPublic(version=issue.resolved_version, at=issue.resolved_at)
            if issue.state is IssueState.RESOLVED and issue.resolved_at is not None
            else None,
        ),
        days=days,
        marks=marks,
        peak=max((d.calls for d in days), default=0),
        affected_calls=[
            IssueAffectedCallPublic(
                call_id=call.id,
                started_at=call.started_at.replace(tzinfo=UTC),
                caller_last_four=crud.caller_last_four(call.caller_number),
                duration_seconds=duration(call),
                result=results.get(call.id, CallCheckStatus.UNCHECKED),
                moment=IssueMomentPublic(
                    at_seconds=moments[call.id].at_seconds,
                    times=moments[call.id].times,
                )
                if call.id in moments
                else IssueMomentPublic(at_seconds=0, times=1),
            )
            for call in calls
        ],
        history=history,
    )
