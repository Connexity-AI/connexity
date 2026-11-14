"""The queries behind one issue's page and the Calls page's issue filter (plan
`plans/2026-11-13-issue-page.md`).

Call times are stored naive, in UTC. A deleted call counts for nothing.
"""

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple

from sqlmodel import Session, col, func, select

from app.models.call import Call, CallComponent, CallEvent
from app.models.check import DecisionRecord, Finding, Issue
from app.models.enums import DecisionKind


class Moment(NamedTuple):
    at_seconds: float
    times: int


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
            Finding.issue_id == issue_id, col(Finding.call_id).in_(call_ids)
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
        ms = [starts[(call_id, key)] for key in keys if (call_id, key) in starts]
        per_call[call_id].append(max(ms) if ms else 0)
    return {
        call_id: Moment(at_seconds=round(min(ms) / 1000, 3), times=len(ms))
        for call_id, ms in per_call.items()
    }


def issue_calls(
    *, session: Session, issue_id: uuid.UUID, since: datetime, limit: int
) -> list[Call]:
    """The latest calls in the period the issue was found on, newest first."""
    return list(
        session.exec(
            select(Call)
            .where(
                col(Call.id).in_(
                    select(Finding.call_id).where(Finding.issue_id == issue_id)
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
        .where(Finding.issue_id == issue_id)
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
                DecisionRecord.kind == DecisionKind.ISSUE_STATE,
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
