"""The score: how an agent, or a whole workspace, did on its checked calls in a period.

A basic formula for now, kept in this one function so a better one can replace it
(Dmytro, 2026-11-18: "we can do very basic score formula for now to not hardcode it and
later devise something better"; "formula ok"):

    score = 100 × (1 − (failed + 0.5 × degraded) / checked calls)

Calls are counted by their result, as on the Calls page: findings of archived issues are
hidden on every call (2026-11-14), so archiving lifts the score for the whole period and
unarchiving lowers it back. Only fixes and improvements should raise it; Readiness never
changes it. It is shown only once onboarding is complete.
"""

import math
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, col, select

from app.crud.call_list import PERIODS
from app.crud.score import (
    ResultCounts,
    ShownFinding,
    result_counts_by_agent,
    result_counts_by_day,
    shown_findings,
)
from app.models.check import Issue
from app.models.score import ScoreMovePublic, ScorePublic
from app.services.issue_list import issue_title
from app.services.onboarding_finish import onboarding_complete

DEGRADED_WEIGHT = 0.5
MAX_MOVES = 5


def score_of(failed: int, degraded: int, checked: int) -> int | None:
    """The formula. None when no call was checked: never 100 by default."""
    if checked <= 0:
        return None
    value = 100 * (1 - (failed + DEGRADED_WEIGHT * degraded) / checked)
    # Halves round up, always (Python's round() would round them to even).
    return math.floor(value + 0.5)


def _weight(fails: list[bool]) -> float:
    """What one call costs: 1 failed, 0.5 degraded, 0 with no finding."""
    if not fails:
        return 0.0
    return 1.0 if any(fails) else DEGRADED_WEIGHT


def _moves(
    session: Session, findings: list[ShownFinding], checked: int
) -> list[ScoreMovePublic]:
    """Each issue's points: the rise if its findings were gone from every call."""
    if checked <= 0 or not findings:
        return []
    by_call: dict[uuid.UUID, list[ShownFinding]] = defaultdict(list)
    for finding in findings:
        by_call[finding.call_id].append(finding)
    points: dict[uuid.UUID, float] = defaultdict(float)
    calls: dict[uuid.UUID, int] = defaultdict(int)
    for found in by_call.values():
        now = _weight([f.fails for f in found])
        for issue_id in {f.issue_id for f in found}:
            without = _weight([f.fails for f in found if f.issue_id != issue_id])
            points[issue_id] += now - without
            calls[issue_id] += 1
    worst = sorted(points, key=lambda issue_id: -points[issue_id])[:MAX_MOVES]
    issues = {
        issue.id: issue
        for issue in session.exec(select(Issue).where(col(Issue.id).in_(worst))).all()
    }
    return [
        ScoreMovePublic(
            issue_id=issue_id,
            title=issue_title(
                issues[issue_id].check_type,
                issues[issue_id].key or None,
                issues[issue_id].subject,
            )
            if issue_id in issues
            else "",
            points=round(100 * points[issue_id] / checked, 1),
            calls=calls[issue_id],
        )
        for issue_id in worst
        if points[issue_id] > 0
    ]


def score(
    *,
    session: Session,
    company_id: uuid.UUID,
    period: str = "30d",
    agent_id: uuid.UUID | None = None,
    version: str | None = None,
    now: datetime | None = None,
    onboarded: bool | None = None,
    with_moves: bool = True,
) -> ScorePublic:
    """The workspace's score, or one agent's (on one agent version when ``version`` is
    given), for the period, with its change against the previous period of the same
    length and the issues that cost it most."""
    days = PERIODS.get(period, 30)
    end = now or datetime.now(UTC)
    start = end - timedelta(days=days)

    def counts(window_start: datetime, window_end: datetime) -> ResultCounts:
        by_agent = result_counts_by_agent(
            session=session,
            company_id=company_id,
            start=window_start,
            end=window_end,
            version=version,
        )
        if agent_id is not None:
            return by_agent.get(agent_id, ResultCounts())
        return sum(by_agent.values(), ResultCounts())

    current = counts(start, end)
    base = ScorePublic(
        period=period,
        checked_calls=current.checked,
        failed_calls=current.failed,
        degraded_calls=current.degraded,
    )
    if onboarded is None:
        onboarded = onboarding_complete(session=session, company_id=company_id)
    if not onboarded:
        base.why_none = (
            "The score comes once onboarding is complete; call `get_next_task`."
        )
        return base
    base.score = score_of(current.failed, current.degraded, current.checked)
    if base.score is None:
        base.why_none = "No checked call in the period yet."
        return base
    before = counts(start - timedelta(days=days), start)
    base.previous = score_of(before.failed, before.degraded, before.checked)
    base.change = None if base.previous is None else base.score - base.previous
    if not with_moves:
        return base
    base.moves = _moves(
        session,
        shown_findings(
            session=session,
            company_id=company_id,
            start=start,
            end=end,
            agent_id=agent_id,
            version=version,
        ),
        current.checked,
    )
    return base


def scores_by_agent(
    *,
    session: Session,
    company_id: uuid.UUID,
    period: str = "30d",
    now: datetime | None = None,
    onboarded: bool | None = None,
) -> dict[uuid.UUID, tuple[int | None, int | None]]:
    """Each agent's score and change for the period, in two queries for all agents.
    Empty before onboarding is complete."""
    if onboarded is None:
        onboarded = onboarding_complete(session=session, company_id=company_id)
    if not onboarded:
        return {}
    days = PERIODS.get(period, 30)
    end = now or datetime.now(UTC)
    start = end - timedelta(days=days)
    current = result_counts_by_agent(
        session=session, company_id=company_id, start=start, end=end
    )
    before = result_counts_by_agent(
        session=session,
        company_id=company_id,
        start=start - timedelta(days=days),
        end=start,
    )
    out: dict[uuid.UUID, tuple[int | None, int | None]] = {}
    for agent_id, counts in current.items():
        now_score = score_of(counts.failed, counts.degraded, counts.checked)
        then = before.get(agent_id)
        then_score = (
            score_of(then.failed, then.degraded, then.checked) if then else None
        )
        change = (
            None if now_score is None or then_score is None else now_score - then_score
        )
        out[agent_id] = (now_score, change)
    return out


def daily_scores(
    *,
    session: Session,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    start: datetime,
    end: datetime | None = None,
    version: str | None = None,
    onboarded: bool | None = None,
) -> dict[date, tuple[int | None, int]]:
    """Each UTC day's score and checked calls for one agent, by the same formula as
    `score` over that day's calls; on agent version ``version`` when given. A day
    without a checked call has none. Empty before onboarding is complete."""
    if onboarded is None:
        onboarded = onboarding_complete(session=session, company_id=company_id)
    if not onboarded:
        return {}
    by_day = result_counts_by_day(
        session=session,
        company_id=company_id,
        agent_id=agent_id,
        start=start,
        end=end or datetime.now(UTC),
        version=version,
    )
    return {
        day: (score_of(c.failed, c.degraded, c.checked), c.checked)
        for day, c in by_day.items()
    }
