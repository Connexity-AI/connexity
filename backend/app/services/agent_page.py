"""The agent page's Overview and `get_agent` (plan `plans/2026-11-14-agent-page.md`)."""

from collections import defaultdict
from datetime import date, datetime

from sqlmodel import Session, col, func, select

from app import crud
from app.crud.issue_list import PERIODS, period_start
from app.crud.issue_page import agent_version_starts, period_days
from app.crud.latency import call_gaps, gap_percentiles
from app.models.agent import Agent
from app.models.agent_list import Period
from app.models.agent_page import (
    AgentLatencyDayPublic,
    AgentPagePublic,
    AgentSystemPublic,
    AgentVersionMarkPublic,
    AgentVersionOptionPublic,
)
from app.models.call import Call, CallComponent
from app.models.component_version import ComponentVersion
from app.services.agent_list import agent_types, live_since
from app.services.issue_list import IssueCounts, issue_counts_by_agent
from app.services.onboarding_finish import onboarding_complete
from app.services.score import daily_scores, score
from app.services.spec import spec_state


def _model(session: Session, agent: Agent, version: str | None) -> str | None:
    """The model the live version links to in the catalogue."""
    if version is None or not agent.platform_agent_id:
        return None
    row = session.exec(
        select(ComponentVersion).where(
            ComponentVersion.agent_id == agent.id,
            ComponentVersion.kind == "agent",
            ComponentVersion.ref == agent.platform_agent_id,
            ComponentVersion.version == version,
        )
    ).first()
    for link in (row.links if row else None) or []:
        if link.get("kind") == "model":
            return link.get("ref")
    return None


def _systems(
    session: Session, agent: Agent, since: datetime, version: str | None
) -> list[AgentSystemPublic]:
    """The n8n workflows the agent's tool calls ran in the period, with the version of
    the most recent call that used each."""
    rows = session.exec(
        select(CallComponent.name, CallComponent.version, Call.started_at)
        .join(Call, col(Call.id) == col(CallComponent.call_id))
        .where(
            Call.agent_id == agent.id,
            col(Call.deleted_at).is_(None),
            col(Call.started_at) >= since.replace(tzinfo=None),
            CallComponent.kind == "skill",
            *([Call.agent_version == version] if version is not None else []),
        )
        .order_by(col(Call.started_at).desc())
    ).all()
    latest: dict[str, str | None] = {}
    for name, version, _started in rows:
        latest.setdefault(name, version)
    return [
        AgentSystemPublic(kind="n8n workflow", name=name, version=version)
        for name, version in sorted(latest.items())
    ]


def agent_versions(
    *, session: Session, agent: Agent, live: str | None
) -> list[AgentVersionOptionPublic]:
    """Every version of the agent that has a call, the latest call's first."""
    rows = session.exec(
        select(Call.agent_version, func.count(), func.max(col(Call.started_at)))
        .where(
            Call.agent_id == agent.id,
            col(Call.deleted_at).is_(None),
            col(Call.agent_version).is_not(None),
        )
        .group_by(col(Call.agent_version))
        .order_by(func.max(col(Call.started_at)).desc())
    ).all()
    return [
        AgentVersionOptionPublic(version=v, calls=int(n), live=v == live)
        for v, n, _last in rows
        if v is not None
    ]


def agent_page(
    *, session: Session, agent: Agent, period: Period, version: str | None = None
) -> AgentPagePublic:
    """One agent's page for the period, its numbers on one agent version when
    ``version`` is given (the period still applies)."""
    since = period_start(period)
    live = crud.current_agent_version(session=session, agent_id=agent.id)
    in_period = [
        Call.agent_id == agent.id,
        col(Call.deleted_at).is_(None),
        col(Call.started_at) >= since.replace(tzinfo=None),
        *([Call.agent_version == version] if version is not None else []),
    ]
    calls = session.exec(select(func.count()).where(*in_period)).one()
    gaps = call_gaps(session=session, agent_ids=[agent.id], since=since)
    version_days: list[date] = []
    if version is not None:
        on_version = dict(
            session.exec(select(Call.id, Call.started_at).where(*in_period)).all()
        )
        gaps = [row for row in gaps if row.call_id in on_version]
        version_days = sorted({started.date() for started in on_version.values()})
    by_day: dict[date, list[int]] = defaultdict(list)
    for row in gaps:
        by_day[row.day].extend(row.gaps)
    overall = gap_percentiles([gap for row in gaps for gap in row.gaps])
    onboarded = onboarding_complete(session=session, company_id=agent.company_id)
    scores = daily_scores(
        session=session,
        agent_id=agent.id,
        company_id=agent.company_id,
        start=since,
        version=version,
        onboarded=onboarded,
    )
    days = [
        AgentLatencyDayPublic(
            day=day,
            p50=gap_percentiles(by_day.get(day, [])).p50,
            replies=len(by_day.get(day, [])),
            score=scores.get(day, (None, 0))[0],
            checked_calls=scores.get(day, (None, 0))[1],
        )
        for day in period_days(since, PERIODS[period])
    ]
    issues = issue_counts_by_agent(
        session=session,
        company_id=agent.company_id,
        period=period,
        agent_id=agent.id,
        version=version,
    ).get(agent.id, IssueCounts())
    first_day = days[0].day if days else since.date()
    marks = [
        AgentVersionMarkPublic(day=started.date(), label=f"Version {version}")
        for version, started in agent_version_starts(
            session=session, agent_id=agent.id
        )[1:]  # the first version is where the agent started, not a change
        if started.date() >= first_day
    ]
    peaks = [d.p50 for d in days if d.p50 is not None]
    return AgentPagePublic(
        id=agent.id,
        name=agent.name,
        platform=agent.platform,
        type=agent_types(
            session=session,
            agents=[agent],
            currents={agent.id: live} if live else {},
        ).get(agent.id),
        live_version=live,
        live_since=live_since(session=session, agent=agent, version=live),
        model=_model(session, agent, live),
        systems=_systems(session, agent, since, version),
        spec=spec_state(crud.latest_spec(session=session, agent_id=agent.id), live),
        period=period,
        calls=calls,
        latency_p50=overall.p50,
        latency_p95=overall.p95,
        latency_replies=overall.answers,
        latency_days=days,
        latency_peak=max(peaks) if peaks else None,
        version_marks=marks,
        score=score(
            session=session,
            company_id=agent.company_id,
            period=period,
            agent_id=agent.id,
            version=version,
            onboarded=onboarded,
            with_moves=False,
        ),
        critical_issues=issues.critical,
        open_issues=issues.open,
        versions=agent_versions(session=session, agent=agent, live=live),
        version=version,
        version_days=version_days,
    )
