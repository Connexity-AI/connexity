"""The Dashboard: where a founder stands with their voice agents, for all agents or one,
over 7, 30 or 90 days (roadmap 10.191; design `designs/screens/Connexity Home.dc.html`).

- **Tiles:** failed and degraded calls with their share (results as on the Calls page),
  latency p95 and p50 over every reply gap (Dmytro, 2026-11-18), and the score (10.19).
- **Calls per day,** with failed and degraded, and the version marks of the agents shown.
- **Areas:** every fixed category. Critical when its findings failed calls, Warning when
  they only degraded them, Healthy when one of its checks ran on the period's calls and
  found nothing, Not checked yet otherwise, with what it waits for. Never green before
  checked.
- **Onboarding strip** while scan, specs and answers are not all done.
"""

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from app import crud
from app.crud.call_list import PERIODS
from app.crud.clarification import state_counts
from app.crud.dashboard import area_counts, calls_per_day, checks_that_ran
from app.crud.issue_page import agent_version_starts
from app.crud.latency import reply_gap_percentiles
from app.models.agent import Agent
from app.models.call_list import CallFilterOption
from app.models.check import Issue
from app.models.dashboard import (
    DashboardArea,
    DashboardDay,
    DashboardLatency,
    DashboardMark,
    DashboardOnboarding,
    DashboardPublic,
    DashboardStep,
)
from app.models.enums import ClarificationState
from app.models.readiness import ReadinessStepKey, ReadinessStepState
from app.services.checks.registry import CHECKS
from app.services.issue_list import issue_title
from app.services.score import score
from app.services.spec import agents_needing_specs

_ORDER = {"critical": 0, "warning": 1, "healthy": 2, "not_checked": 3}


def _share(part: int, whole: int) -> float | None:
    return round(part / whole, 3) if whole else None


def _onboarding(
    session: Session, company_id: uuid.UUID, areas_checked: int, areas_total: int
) -> DashboardOnboarding | None:
    readiness = crud.get_readiness(session=session, company_id=company_id, mcp_url=None)
    scanned = any(
        step.key is ReadinessStepKey.FIRST_SCAN
        and step.state is ReadinessStepState.DONE
        for step in readiness.steps
    )
    specs = scanned and not agents_needing_specs(session=session, company_id=company_id)
    counts = state_counts(session=session, company_id=company_id)
    answered = counts[ClarificationState.ANSWERED]
    total = answered + counts[ClarificationState.OPEN]
    answers = specs and counts[ClarificationState.OPEN] == 0
    complete = scanned and specs and answers
    if complete:
        return None
    return DashboardOnboarding(
        steps=[
            DashboardStep(key="scan", label="Scan", done=scanned),
            DashboardStep(key="spec", label="Spec", done=specs),
            DashboardStep(
                key="answers",
                label=f"Answers {answered} of {total}" if total else "Answers",
                done=answers,
            ),
            DashboardStep(key="complete", label="Complete", done=False),
        ],
        areas_checked=areas_checked,
        areas_total=areas_total,
    )


def dashboard(
    *,
    session: Session,
    company_id: uuid.UUID,
    period: str = "30d",
    agent_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> DashboardPublic:
    days = PERIODS.get(period, 30)
    end = (now or datetime.now(UTC)).astimezone(UTC)
    start = end - timedelta(days=days)

    linked = list(
        session.exec(
            select(Agent)
            .where(
                Agent.company_id == company_id,
                col(Agent.integration_id).is_not(None),
                col(Agent.platform_agent_id).is_not(None),
            )
            .order_by(col(Agent.name))
        ).all()
    )
    shown = [a for a in linked if agent_id is None or a.id == agent_id]

    per_day = calls_per_day(
        session=session, company_id=company_id, start=start, end=end, agent_id=agent_id
    )
    calls = sum(d.calls for d in per_day.values())
    failed = sum(d.failed for d in per_day.values())
    degraded = sum(d.degraded for d in per_day.values())
    first_day = start.date()
    day_list = [
        DashboardDay(
            day=day,
            calls=per_day[day].calls if day in per_day else 0,
            failed=per_day[day].failed if day in per_day else 0,
            degraded=per_day[day].degraded if day in per_day else 0,
        )
        for day in (first_day + timedelta(days=n) for n in range(days + 1))
        if day <= end.date()
    ]

    marks = []
    for agent in shown:
        for version, started in agent_version_starts(
            session=session, agent_id=agent.id
        ):
            if start <= started < end:
                marks.append(
                    DashboardMark(
                        day=started.date(), version=version, agent_name=agent.name
                    )
                )
    marks.sort(key=lambda mark: mark.day)

    # Over every agent whose calls count, as the results and the score do.
    counted = (
        [agent_id]
        if agent_id is not None
        else list(
            session.exec(select(Agent.id).where(Agent.company_id == company_id)).all()
        )
    )
    gaps = reply_gap_percentiles(
        session=session,
        agent_ids=counted,
        since=start,
        until=end,
    )

    # Areas: every fixed category.
    found = area_counts(
        session=session, company_id=company_id, start=start, end=end, agent_id=agent_id
    )
    ran = checks_that_ran(
        session=session, company_id=company_id, start=start, end=end, agent_id=agent_id
    )
    checks_by_area: dict[str, set[str]] = defaultdict(set)
    for check in CHECKS:
        checks_by_area[check.category].add(check.type)
    tops = [c.top_issue for c in found.values() if c.top_issue is not None]
    issues = {
        issue.id: issue
        for issue in session.exec(select(Issue).where(col(Issue.id).in_(tops))).all()
    }
    areas = []
    for category in crud.list_categories(session=session):
        counts = found.get(category.key)
        has_checks = bool(checks_by_area.get(category.key))
        checked = bool(checks_by_area.get(category.key, set()) & ran)
        if counts and counts.failed:
            status = "critical"
        elif counts and counts.degraded:
            status = "warning"
        elif checked:
            status = "healthy"
        else:
            status = "not_checked"
        top = issues.get(counts.top_issue) if counts and counts.top_issue else None
        areas.append(
            DashboardArea(
                key=category.key,
                name=category.name,
                status=status,
                waits_for=None
                if status != "not_checked"
                else (
                    "No calls checked yet"
                    if has_checks
                    else "No check covers this area yet"
                ),
                failed=counts.failed if counts else 0,
                degraded=counts.degraded if counts else 0,
                share=_share(counts.failed + counts.degraded, calls)
                if counts
                else None,
                top_issue_id=top.id if top else None,
                top_issue_title=issue_title(top.check_type, top.key or None)
                if top
                else None,
            )
        )
    areas.sort(key=lambda a: (_ORDER[a.status], -(a.failed + a.degraded)))
    checked_areas = sum(1 for a in areas if a.status != "not_checked")

    return DashboardPublic(
        period=period,
        agent_id=agent_id,
        agents=[CallFilterOption(value=str(a.id), label=a.name) for a in linked],
        agents_counted=len(shown),
        calls=calls,
        onboarding=_onboarding(session, company_id, checked_areas, len(areas)),
        score=score(
            session=session,
            company_id=company_id,
            period=period,
            agent_id=agent_id,
            now=end,
        ),
        failed=failed,
        failed_share=_share(failed, calls),
        degraded=degraded,
        degraded_share=_share(degraded, calls),
        latency=DashboardLatency(p50=gaps.p50, p95=gaps.p95, answers=gaps.answers),
        days=day_list,
        marks=marks,
        areas=areas,
    )
