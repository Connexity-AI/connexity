"""The queries behind one issue's page and the Calls page's issue filter (plan
`plans/2026-11-13-issue-page.md`).

Call times are stored naive, in UTC. A deleted call counts for nothing.
"""

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple

from sqlmodel import Session, col, func, select

from app.crud.check import counted_finding, version_reaches
from app.models.call import Call, CallComponent, CallEvent
from app.models.check import DecisionRecord, Finding, Issue
from app.models.enums import DecisionKind, TraceSource


class Moment(NamedTuple):
    at_seconds: float
    times: int


class SinceVersion(NamedTuple):
    """An agent's real calls on a version or a later one, and the issue's among them."""

    live_at: datetime | None
    calls: int
    calls_with_issue: int
    last_call_id: uuid.UUID | None
    last_call_at: datetime | None


def _naive(moment: datetime) -> datetime:
    return moment.astimezone(UTC).replace(tzinfo=None) if moment.tzinfo else moment


def issue_moments(
    *, session: Session, issue_id: uuid.UUID, call_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Moment]:
    """Where the issue first happened in each call, and how many times.

    A finding's moment is the last event it points at, as on the single call.
    """
    if not call_ids:
        return {}
    findings = session.exec(
        select(Finding.call_id, Finding.event_keys).where(
            Finding.issue_id == issue_id,
            counted_finding(),
            col(Finding.call_id).in_(call_ids),
        )
    ).all()
    keys = {key for _, event_keys in findings for key in event_keys}
    starts: dict[tuple[uuid.UUID, str], int] = (
        {
            (call_id, key): start or 0
            for call_id, key, start in session.exec(
                select(CallEvent.call_id, CallEvent.key, CallEvent.start_ms).where(
                    col(CallEvent.call_id).in_(call_ids), col(CallEvent.key).in_(keys)
                )
            ).all()
        }
        if keys
        else {}
    )
    per_call: dict[uuid.UUID, list[int]] = defaultdict(list)
    for call_id, keys in findings:
        if not keys:
            # A finding on the whole call (a broken spec rule) has no moment.
            continue
        ms = [starts[(call_id, key)] for key in keys if (call_id, key) in starts]
        per_call[call_id].append(max(ms) if ms else 0)
    return {
        call_id: Moment(at_seconds=round(min(ms) / 1000, 3), times=len(ms))
        for call_id, ms in per_call.items()
    }


class SpecSeen(NamedTuple):
    probability: float | None
    reason: str | None


def issue_spec_findings(
    *, session: Session, issue_id: uuid.UUID, call_ids: list[uuid.UUID]
) -> dict[uuid.UUID, SpecSeen]:
    """For a broken spec rule: the classifier's probability on each call, the highest
    when there are several, and the LLM's reason, when one gave it."""
    if not call_ids:
        return {}
    seen: dict[uuid.UUID, SpecSeen] = {}
    for call_id, detail in session.exec(
        select(Finding.call_id, Finding.detail)
        .where(
            Finding.issue_id == issue_id,
            counted_finding(),
            col(Finding.call_id).in_(call_ids),
        )
        .order_by(col(Finding.created_at))
    ).all():
        value = (detail or {}).get("probability")
        reason = (detail or {}).get("reason")
        before = seen.get(call_id, SpecSeen(None, None))
        probability = float(value) if isinstance(value, int | float) else None
        seen[call_id] = SpecSeen(
            probability=max(
                (p for p in (before.probability, probability) if p is not None),
                default=None,
            ),
            reason=reason if isinstance(reason, str) and reason else before.reason,
        )
    return seen


def newest_finding(*, session: Session, issue_id: uuid.UUID) -> Finding | None:
    return session.exec(
        select(Finding)
        .where(Finding.issue_id == issue_id, counted_finding())
        .order_by(col(Finding.created_at).desc(), col(Finding.id).desc())
        .limit(1)
    ).first()


def issue_calls(
    *, session: Session, issue_id: uuid.UUID, since: datetime, limit: int
) -> list[Call]:
    """The latest calls in the period the issue was found on, newest first."""
    return list(
        session.exec(
            select(Call)
            .where(
                col(Call.id).in_(
                    select(Finding.call_id).where(
                        Finding.issue_id == issue_id, counted_finding()
                    )
                ),
                col(Call.deleted_at).is_(None),
                col(Call.started_at) >= _naive(since),
            )
            .order_by(col(Call.started_at).desc(), col(Call.id))
            .limit(limit)
        ).all()
    )


def issue_calls_per_day(
    *, session: Session, issue_id: uuid.UUID, since: datetime
) -> dict[date, int]:
    """Distinct calls per day (UTC) in the period the issue was found on."""
    day = func.date(col(Call.started_at))
    rows = session.exec(
        select(day, func.count(func.distinct(col(Call.id))))
        .join(Finding, col(Finding.call_id) == col(Call.id))
        .where(
            Finding.issue_id == issue_id,
            counted_finding(),
            col(Call.deleted_at).is_(None),
            col(Call.started_at) >= _naive(since),
        )
        .group_by(day)
    ).all()
    return dict(rows)


def agent_calls_since(*, session: Session, agent_id: uuid.UUID, since: datetime) -> int:
    return session.exec(
        select(func.count()).where(
            Call.agent_id == agent_id,
            col(Call.deleted_at).is_(None),
            col(Call.started_at) >= _naive(since),
        )
    ).one()


def issue_calls_between(
    *, session: Session, issue_id: uuid.UUID, start: datetime, end: datetime
) -> int:
    """Distinct calls the issue was found on that started in ``[start, end)``."""
    return session.exec(
        select(func.count(func.distinct(col(Finding.call_id))))
        .join(Call, col(Call.id) == col(Finding.call_id))
        .where(
            Finding.issue_id == issue_id,
            counted_finding(),
            col(Call.deleted_at).is_(None),
            col(Call.started_at) >= _naive(start),
            col(Call.started_at) < _naive(end),
        )
    ).one()


def agent_calls_between(
    *, session: Session, agent_id: uuid.UUID, start: datetime, end: datetime
) -> int:
    return session.exec(
        select(func.count()).where(
            Call.agent_id == agent_id,
            col(Call.deleted_at).is_(None),
            col(Call.started_at) >= _naive(start),
            col(Call.started_at) < _naive(end),
        )
    ).one()


def agent_version_starts(
    *, session: Session, agent_id: uuid.UUID
) -> list[tuple[str, datetime]]:
    """Each agent version and when the first call on it started, earliest first.

    Read from the calls, not from when Connexity first recorded the version.
    """
    rows = session.exec(
        select(CallComponent.version, func.min(col(Call.started_at)))
        .join(Call, col(Call.id) == col(CallComponent.call_id))
        .where(
            Call.agent_id == agent_id,
            CallComponent.kind == "agent",
            col(CallComponent.version).is_not(None),
            col(Call.deleted_at).is_(None),
        )
        .group_by(col(CallComponent.version))
        .order_by(func.min(col(Call.started_at)))
    ).all()
    return [
        (version, started.replace(tzinfo=UTC)) for version, started in rows if version
    ]


def first_finding_call(*, session: Session, issue_id: uuid.UUID) -> Call | None:
    """The earliest call the issue was found on."""
    return session.exec(
        select(Call)
        .join(Finding, col(Finding.call_id) == col(Call.id))
        .where(Finding.issue_id == issue_id, counted_finding())
        .order_by(col(Call.started_at), col(Call.id))
        .limit(1)
    ).first()


def issue_decisions(*, session: Session, issue: Issue) -> list[DecisionRecord]:
    """The issue's decision records, newest first."""
    return list(
        session.exec(
            select(DecisionRecord)
            .where(
                DecisionRecord.agent_id == issue.agent_id,
                col(DecisionRecord.kind).in_(
                    (DecisionKind.ISSUE_STATE, DecisionKind.FINDINGS_COUNTED)
                ),
                DecisionRecord.subject == str(issue.id),
            )
            .order_by(
                col(DecisionRecord.created_at).desc(), col(DecisionRecord.id).desc()
            )
        ).all()
    )


def period_days(since: datetime, days: int) -> list[date]:
    start = since.astimezone(UTC).date()
    return [start + timedelta(days=i) for i in range(1, days + 1)]


def issue_calls_per_version(
    *, session: Session, issue_id: uuid.UUID, since: datetime
) -> list[tuple[str | None, int]]:
    """Distinct calls the issue was found on since ``since``, per agent version (the
    version the call reported; None when it reported none), most calls first."""
    rows = session.exec(
        select(Call.agent_version, func.count(func.distinct(col(Call.id))))
        .join(Finding, col(Finding.call_id) == col(Call.id))
        .where(
            Finding.issue_id == issue_id,
            counted_finding(),
            col(Call.deleted_at).is_(None),
            col(Call.started_at) >= _naive(since),
        )
        .group_by(col(Call.agent_version))
        .order_by(func.count(func.distinct(col(Call.id))).desc())
    ).all()
    return list(rows)


def latest_agent_version(*, session: Session, agent_id: uuid.UUID) -> str | None:
    """The agent version on the agent's newest call: what is live on real calls."""
    return session.exec(
        select(Call.agent_version)
        .where(
            Call.agent_id == agent_id,
            col(Call.deleted_at).is_(None),
            col(Call.agent_version).is_not(None),
        )
        .order_by(col(Call.started_at).desc())
        .limit(1)
    ).first()


def issue_findings_on_calls(
    *, session: Session, issue_id: uuid.UUID, call_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[Finding]]:
    """The issue's findings on each of these calls, in the order they were stored."""
    found: dict[uuid.UUID, list[Finding]] = defaultdict(list)
    if not call_ids:
        return found
    for finding in session.exec(
        select(Finding)
        .where(
            Finding.issue_id == issue_id,
            counted_finding(),
            col(Finding.call_id).in_(call_ids),
        )
        .order_by(col(Finding.created_at))
    ).all():
        found[finding.call_id].append(finding)
    return found


def call_agent_versions(
    *, session: Session, call_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str | None]:
    if not call_ids:
        return {}
    return dict(
        session.exec(
            select(Call.id, Call.agent_version).where(col(Call.id).in_(call_ids))
        ).all()
    )


def issue_since_version(
    *, session: Session, issue: Issue, version: str
) -> SinceVersion:
    """What happened on real calls since ``version`` went live: the agent's calls that
    ran it or a later version, and how many of them have the issue.

    A call counts by the version it ran (``version_reaches``, the rule that makes a
    fix live), so a call an older version still served after ``version`` went live is
    left out.
    """
    real = (
        Call.agent_id == issue.agent_id,
        Call.source == TraceSource.PRODUCTION,
        col(Call.deleted_at).is_(None),
        col(Call.agent_version).is_not(None),
    )
    per_version = session.exec(
        select(Call.agent_version, func.count(), func.min(col(Call.started_at)))
        .where(*real)
        .group_by(col(Call.agent_version))
    ).all()
    reached = [
        (name, calls, first)
        for name, calls, first in per_version
        if version_reaches(name, version)
    ]
    if not reached:
        return SinceVersion(None, 0, 0, None, None)
    names = [name for name, _, _ in reached]
    on_them = (
        *real,
        col(Call.agent_version).in_(names),
        col(Call.id).in_(
            select(Finding.call_id).where(
                Finding.issue_id == issue.id, counted_finding()
            )
        ),
    )
    last = session.exec(
        select(Call.id, Call.started_at)
        .where(*on_them)
        .order_by(col(Call.started_at).desc(), col(Call.id))
        .limit(1)
    ).first()
    return SinceVersion(
        live_at=min(first for _, _, first in reached).replace(tzinfo=UTC),
        calls=sum(calls for _, calls, _ in reached),
        calls_with_issue=session.exec(select(func.count()).where(*on_them)).one(),
        last_call_id=last[0] if last else None,
        last_call_at=last[1].replace(tzinfo=UTC) if last else None,
    )
