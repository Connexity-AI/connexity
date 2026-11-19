"""The agent page's Overview and `get_agent` (plan `plans/2026-11-14-agent-page.md`)."""

from collections import defaultdict
from datetime import UTC, date, datetime

from sqlmodel import Session, col, func, select

from app import crud
from app.crud.issue_list import PERIODS, period_start
from app.crud.issue_page import agent_version_starts, period_days
from app.crud.latency import average, call_latencies
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
from app.services.agent_list import agent_types
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


def _live_since(session: Session, agent: Agent, version: str | None) -> datetime | None:
    """The first call on the live version since the agent last ran any other one, so
    a version it went back to counts from its return."""
    if version is None:
        return None
    other = session.exec(
        select(func.max(col(Call.started_at))).where(
            Call.agent_id == agent.id,
            col(Call.deleted_at).is_(None),
            col(Call.agent_version).is_not(None),
            Call.agent_version != version,
        )
    ).one()
    query = select(func.min(col(Call.started_at))).where(
        Call.agent_id == agent.id,
        col(Call.deleted_at).is_(None),
        Call.agent_version == version,
    )
    if other is not None:
        query = query.where(col(Call.started_at) > other)
    first = session.exec(query).one()
    return first.replace(tzinfo=UTC) if first else None


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
    latencies = call_latencies(session=session, agent_ids=[agent.id], since=since)
    version_days: list[date] = []
    if version is not None:
        on_version = dict(
            session.exec(select(Call.id, Call.started_at).where(*in_period)).all()
        )
        latencies = [row for row in latencies if row.call_id in on_version]
        version_days = sorted({started.date() for started in on_version.values()})
    by_day: dict[date, list[float]] = defaultdict(list)
    for row in latencies:
        by_day[row.day].append(row.seconds)
    days = [
        AgentLatencyDayPublic(
            day=day,
            seconds=average(by_day.get(day, [])),
            calls=len(by_day.get(day, [])),
        )
        for day in period_days(since, PERIODS[period])
    ]
    first_day = days[0].day if days else since.date()
    marks = [
        AgentVersionMarkPublic(day=started.date(), label=f"Version {version}")
        for version, started in agent_version_starts(
            session=session, agent_id=agent.id
        )[1:]  # the first version is where the agent started, not a change
        if started.date() >= first_day
    ]
    peaks = [d.seconds for d in days if d.seconds is not None]
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
        live_since=_live_since(session, agent, live),
        model=_model(session, agent, live),
        systems=_systems(session, agent, since, version),
        spec=spec_state(crud.latest_spec(session=session, agent_id=agent.id), live),
        period=period,
        calls=calls,
        latency_seconds=average([row.seconds for row in latencies]),
        latency_calls=len(latencies),
        latency_days=days,
        latency_peak=max(peaks) if peaks else None,
        version_marks=marks,
        versions=agent_versions(session=session, agent=agent, live=live),
        version=version,
        version_days=version_days,
    )
