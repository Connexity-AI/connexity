"""The counts the score is made from: calls by result in a window, per agent, and the
shown findings on those calls by issue. Results are worked out exactly as the Calls page
works them out (`crud/call_list.py`); findings of archived issues are left out on every
call (`shown_finding`). Call times are stored naive, in UTC.
"""

import uuid
from datetime import UTC, date, datetime
from typing import NamedTuple

from sqlalchemy import and_
from sqlmodel import Session, col, func, select

from app.crud.call_list import _counting, _ran
from app.crud.check import shown_finding
from app.models.call import Call
from app.models.check import Finding
from app.models.enums import FindingEffect


class ResultCounts(NamedTuple):
    failed: int = 0
    degraded: int = 0
    clean: int = 0

    @property
    def checked(self) -> int:
        return self.failed + self.degraded + self.clean

    def __add__(self, other: tuple[int, ...]) -> "ResultCounts":
        return ResultCounts(*(a + b for a, b in zip(self, other, strict=True)))


def _naive(moment: datetime) -> datetime:
    return moment.astimezone(UTC).replace(tzinfo=None) if moment.tzinfo else moment


def _window(company_id: uuid.UUID, start: datetime, end: datetime) -> list:  # noqa: ANN401
    return [
        Call.company_id == company_id,
        col(Call.deleted_at).is_(None),
        col(Call.started_at) >= _naive(start),
        col(Call.started_at) < _naive(end),
    ]


def result_counts_by_agent(
    *,
    session: Session,
    company_id: uuid.UUID,
    start: datetime,
    end: datetime,
    version: str | None = None,
) -> dict[uuid.UUID, ResultCounts]:
    """Each agent's failed, degraded and clean calls that started in ``[start, end)``,
    on agent version ``version`` when given. Unchecked calls are left out."""
    fails = _counting(FindingEffect.FAILS)
    counts = _counting()
    rows = session.exec(
        select(
            Call.agent_id,
            func.count().filter(fails),
            func.count().filter(and_(counts, ~fails)),
            func.count().filter(and_(~counts, _ran())),
        )
        .where(
            *_window(company_id, start, end),
            *([Call.agent_version == version] if version is not None else []),
        )
        .group_by(col(Call.agent_id))
    ).all()
    return {
        agent_id: ResultCounts(int(failed), int(degraded), int(clean))
        for agent_id, failed, degraded, clean in rows
    }


def result_counts_by_day(
    *,
    session: Session,
    company_id: uuid.UUID,
    agent_id: uuid.UUID,
    start: datetime,
    end: datetime,
    version: str | None = None,
) -> dict[date, ResultCounts]:
    """One agent's failed, degraded and clean calls by the UTC day they started, in
    ``[start, end)``, on agent version ``version`` when given. Unchecked calls are left
    out, as in `result_counts_by_agent`."""
    fails = _counting(FindingEffect.FAILS)
    counts = _counting()
    day = func.date(col(Call.started_at))
    rows = session.exec(
        select(
            day,
            func.count().filter(fails),
            func.count().filter(and_(counts, ~fails)),
            func.count().filter(and_(~counts, _ran())),
        )
        .where(
            *_window(company_id, start, end),
            Call.agent_id == agent_id,
            *([Call.agent_version == version] if version is not None else []),
        )
        .group_by(day)
    ).all()
    return {
        when: ResultCounts(int(failed), int(degraded), int(clean))
        for when, failed, degraded, clean in rows
    }


class ShownFinding(NamedTuple):
    call_id: uuid.UUID
    agent_id: uuid.UUID
    issue_id: uuid.UUID
    fails: bool


def shown_findings(
    *,
    session: Session,
    company_id: uuid.UUID,
    start: datetime,
    end: datetime,
    agent_id: uuid.UUID | None = None,
    version: str | None = None,
) -> list[ShownFinding]:
    """Every shown finding on calls that started in ``[start, end)``, one row each."""
    query = (
        select(Finding.call_id, Call.agent_id, Finding.issue_id, Finding.effect)
        .join(Call, col(Call.id) == col(Finding.call_id))
        .where(*_window(company_id, start, end), shown_finding())
    )
    if agent_id is not None:
        query = query.where(Call.agent_id == agent_id)
    if version is not None:
        query = query.where(Call.agent_version == version)
    return [
        ShownFinding(call_id, call_agent, issue_id, effect == FindingEffect.FAILS)
        for call_id, call_agent, issue_id, effect in session.exec(query).all()
    ]
