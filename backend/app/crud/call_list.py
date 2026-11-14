"""A workspace's calls, newest first, with search, filters, tiles and each call's result
and worst finding. Used by the Calls page and `list_calls` (plan
`plans/2026-11-13-calls-page.md`).

A call's result follows `call_check_statuses`: failed when a finding fails it,
degraded when one only flags it, clean when a check ran and found nothing, unchecked
otherwise. A finding counts whenever its check was added (Dmytro, 2026-11-13).
"""

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from sqlalchemy import ColumnElement, String, and_, case, cast, exists, func, or_
from sqlmodel import Session, col, select

from app.crud.check import shown_finding
from app.models.agent import Agent
from app.models.call import Call
from app.models.category import Category
from app.models.check import CallCheck, Finding, Issue
from app.models.enums import CallCheckStatus, CheckOutcome, FindingEffect

PERIODS = {"7d": 7, "30d": 30, "90d": 90}

_DIGITS = re.compile(r"\D")
# A search that is a phone number, whole or its last digits: "+1 732-555-0142", "4821".
_PHONE = re.compile(r"^\+?[\d\s().-]{3,}$")


class CallFilters(NamedTuple):
    period: str = "30d"
    agent_id: uuid.UUID | None = None
    result: CallCheckStatus | None = None
    category: str | None = None  # a category key
    query: str | None = None
    # Only calls this issue was found on, archived or not (the issue page's link).
    issue_id: uuid.UUID | None = None


class WorstFinding(NamedTuple):
    check_type: str
    key: str | None
    category: str
    critical: bool


class CallRow(NamedTuple):
    call: Call
    agent_name: str
    result: CallCheckStatus
    worst: WorstFinding | None


class CallTiles(NamedTuple):
    calls: int
    failed: int
    degraded: int
    clean: int
    unchecked: int


def _counting(effect: FindingEffect | None = None) -> ColumnElement[bool]:
    """The call has a shown finding, of ``effect`` if given."""
    condition: ColumnElement[bool] = and_(Finding.call_id == Call.id, shown_finding())
    if effect is not None:
        condition = and_(condition, Finding.effect == effect)
    return exists().where(condition)


def _ran() -> ColumnElement[bool]:
    return exists().where(
        CallCheck.call_id == Call.id, CallCheck.outcome == CheckOutcome.RAN
    )


def _result_is(result: CallCheckStatus) -> ColumnElement[bool]:
    if result is CallCheckStatus.FAILED:
        return _counting(FindingEffect.FAILS)
    if result is CallCheckStatus.DEGRADED:
        return and_(_counting(), ~_counting(FindingEffect.FAILS))
    if result is CallCheckStatus.CLEAN:
        return and_(~_counting(), _ran())
    return and_(~_counting(), ~_ran())


def caller_last_four(number: str | None) -> str | None:
    digits = _DIGITS.sub("", number or "")
    return digits[-4:] if len(digits) >= 4 else None


def _search(query: str) -> ColumnElement[bool]:
    text = query.strip()
    if _PHONE.match(text):
        digits = _DIGITS.sub("", text)
        stored = func.regexp_replace(col(Call.caller_number), r"\D", "", "g")
        return stored.like(f"%{digits}")
    return or_(
        col(Call.external_id) == text,
        cast(col(Call.id), String) == text.lower(),
    )


def _where(
    company_id: uuid.UUID, filters: CallFilters, *, with_result: bool
) -> list[ColumnElement[bool]]:
    since = datetime.now(UTC) - timedelta(days=PERIODS.get(filters.period, 30))
    conditions: list[ColumnElement[bool]] = [
        Call.company_id == company_id,
        col(Call.deleted_at).is_(None),
        # Call times are stored naive, in UTC.
        col(Call.started_at) >= since.replace(tzinfo=None),
    ]
    if filters.agent_id is not None:
        conditions.append(Call.agent_id == filters.agent_id)
    if filters.query and filters.query.strip():
        conditions.append(_search(filters.query))
    if filters.category:
        conditions.append(
            exists().where(
                Finding.call_id == Call.id,
                Issue.id == Finding.issue_id,
                Category.id == Issue.category_id,
                Category.key == filters.category,
                shown_finding(),
            )
        )
    if filters.issue_id is not None:
        conditions.append(
            exists().where(
                Finding.call_id == Call.id, Finding.issue_id == filters.issue_id
            )
        )
    if with_result and filters.result is not None:
        conditions.append(_result_is(filters.result))
    return conditions


def _results(
    session: Session, call_ids: list[uuid.UUID]
) -> dict[uuid.UUID, CallCheckStatus]:
    if not call_ids:
        return {}
    rows = session.exec(
        select(
            Call.id,
            _counting(FindingEffect.FAILS),
            _counting(),
            _ran(),
        ).where(col(Call.id).in_(call_ids))
    ).all()
    results = {}
    for call_id, fails, counts, ran in rows:
        if fails:
            results[call_id] = CallCheckStatus.FAILED
        elif counts:
            results[call_id] = CallCheckStatus.DEGRADED
        elif ran:
            results[call_id] = CallCheckStatus.CLEAN
        else:
            results[call_id] = CallCheckStatus.UNCHECKED
    return results


def _worst(
    session: Session, call_ids: list[uuid.UUID]
) -> dict[uuid.UUID, WorstFinding]:
    """Each call's worst finding: failing before flagging, then by the category's
    order, then the earliest raised."""
    if not call_ids:
        return {}
    rows = session.exec(
        select(
            Finding.call_id,
            Finding.check_type,
            Finding.key,
            Category.name,
            Finding.effect,
        )
        .join(Issue, col(Issue.id) == col(Finding.issue_id))
        .join(Category, col(Category.id) == col(Issue.category_id))
        .where(col(Finding.call_id).in_(call_ids), shown_finding())
        .order_by(
            col(Finding.call_id),
            case((col(Finding.effect) == FindingEffect.FAILS, 0), else_=1),
            col(Category.position),
            col(Finding.created_at),
        )
    ).all()
    worst: dict[uuid.UUID, WorstFinding] = {}
    for call_id, check_type, key, category, effect in rows:
        if call_id not in worst:
            worst[call_id] = WorstFinding(
                check_type=check_type,
                key=key,
                category=category,
                critical=effect == FindingEffect.FAILS,
            )
    return worst


def list_workspace_calls(
    *,
    session: Session,
    company_id: uuid.UUID,
    filters: CallFilters,
    offset: int,
    limit: int,
) -> tuple[list[CallRow], bool]:
    """A page of the workspace's calls, newest first, and whether more follow."""
    rows = session.exec(
        select(Call, Agent.name)
        .join(Agent, col(Agent.id) == col(Call.agent_id))
        .where(*_where(company_id, filters, with_result=True))
        .order_by(col(Call.started_at).desc(), col(Call.id))
        .offset(offset)
        .limit(limit + 1)
    ).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    ids = [call.id for call, _ in rows]
    results = _results(session, ids)
    worst = _worst(session, ids)
    return (
        [
            CallRow(
                call=call,
                agent_name=name,
                result=results.get(call.id, CallCheckStatus.UNCHECKED),
                worst=worst.get(call.id),
            )
            for call, name in rows
        ],
        has_more,
    )


def workspace_call_tiles(
    *, session: Session, company_id: uuid.UUID, filters: CallFilters
) -> CallTiles:
    """How many calls match the filters, and how many of those are failed, degraded,
    clean or unchecked. The result filter does not narrow the tiles."""
    fails = _counting(FindingEffect.FAILS)
    counts = _counting()
    ran = _ran()
    row = session.exec(
        select(
            func.count(),
            func.count().filter(fails),
            func.count().filter(and_(counts, ~fails)),
            func.count().filter(and_(~counts, ran)),
            func.count().filter(and_(~counts, ~ran)),
        )
        .select_from(Call)
        .where(*_where(company_id, filters, with_result=False))
    ).one()
    return CallTiles(*[int(value) for value in row])
