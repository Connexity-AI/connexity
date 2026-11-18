"""The counts behind the Dashboard: calls per day by result, and each area's (category's)
failed and degraded calls, top issue and whether any of its checks ran. Results count as
on the Calls page; findings of archived issues are left out (`shown_finding`). Call times
are stored naive, in UTC.
"""

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import NamedTuple

from sqlalchemy import and_, func
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select

from app.crud.call_list import _counting
from app.crud.check import shown_finding
from app.models.call import Call
from app.models.category import Category
from app.models.check import CallCheck, Finding, Issue
from app.models.enums import CheckOutcome, FindingEffect


def _naive(moment: datetime) -> datetime:
    return moment.astimezone(UTC).replace(tzinfo=None) if moment.tzinfo else moment


def _window(
    company_id: uuid.UUID,
    start: datetime,
    end: datetime,
    agent_id: uuid.UUID | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = [
        Call.company_id == company_id,
        col(Call.deleted_at).is_(None),
        col(Call.started_at) >= _naive(start),
        col(Call.started_at) < _naive(end),
    ]
    if agent_id is not None:
        conditions.append(Call.agent_id == agent_id)
    return conditions


class Day(NamedTuple):
    day: date
    calls: int
    failed: int
    degraded: int


def calls_per_day(
    *,
    session: Session,
    company_id: uuid.UUID,
    start: datetime,
    end: datetime,
    agent_id: uuid.UUID | None = None,
) -> dict[date, Day]:
    """Calls, failed and degraded per UTC day, for the days that had calls."""
    fails = _counting(FindingEffect.FAILS)
    day = func.date(col(Call.started_at))
    rows = session.exec(
        select(
            day,
            func.count(),
            func.count().filter(fails),
            func.count().filter(and_(_counting(), ~fails)),
        )
        .where(*_window(company_id, start, end, agent_id))
        .group_by(day)
    ).all()
    return {
        d: Day(d, int(calls), int(failed), int(degraded))
        for d, calls, failed, degraded in rows
    }


class AreaCounts(NamedTuple):
    failed: int
    degraded: int
    # The issue found on the most calls in the area, and on how many.
    top_issue: uuid.UUID | None
    top_calls: int


def area_counts(
    *,
    session: Session,
    company_id: uuid.UUID,
    start: datetime,
    end: datetime,
    agent_id: uuid.UUID | None = None,
) -> dict[str, AreaCounts]:
    """Per category key: calls a finding of that area failed, calls it only degraded,
    and its top issue. Only areas with a shown finding in the window."""
    rows = session.exec(
        select(
            Category.key,
            Finding.call_id,
            Finding.issue_id,
            Finding.effect,
        )
        .join(Call, col(Call.id) == col(Finding.call_id))
        .join(Issue, col(Issue.id) == col(Finding.issue_id))
        .join(Category, col(Category.id) == col(Issue.category_id))
        .where(*_window(company_id, start, end, agent_id), shown_finding())
    ).all()
    fails: dict[str, dict[uuid.UUID, bool]] = defaultdict(dict)
    issue_calls: dict[str, dict[uuid.UUID, set[uuid.UUID]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for key, call_id, issue_id, effect in rows:
        failed = effect == FindingEffect.FAILS
        fails[key][call_id] = fails[key].get(call_id, False) or failed
        issue_calls[key][issue_id].add(call_id)
    out: dict[str, AreaCounts] = {}
    for key, calls in fails.items():
        top = max(issue_calls[key].items(), key=lambda pair: len(pair[1]))
        out[key] = AreaCounts(
            failed=sum(calls.values()),
            degraded=sum(1 for failed in calls.values() if not failed),
            top_issue=top[0],
            top_calls=len(top[1]),
        )
    return out


def checks_that_ran(
    *,
    session: Session,
    company_id: uuid.UUID,
    start: datetime,
    end: datetime,
    agent_id: uuid.UUID | None = None,
) -> set[str]:
    """The check types that ran on at least one call in the window."""
    return set(
        session.exec(
            select(CallCheck.check_type)
            .join(Call, col(Call.id) == col(CallCheck.call_id))
            .where(
                *_window(company_id, start, end, agent_id),
                CallCheck.outcome == CheckOutcome.RAN,
            )
            .distinct()
        ).all()
    )
