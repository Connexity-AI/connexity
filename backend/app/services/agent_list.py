"""The Agents page and `list_agents`' type and calls (plan
`plans/2026-11-14-agents-page.md`)."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Session, col, func, select

from app import crud
from app.crud.issue_list import calls_by_agent, period_start
from app.crud.latency import agent_gap_percentiles
from app.models.agent import Agent
from app.models.agent_list import (
    AgentListItemPublic,
    AgentListPublic,
    AgentType,
    Period,
)
from app.models.call import Call
from app.models.component_version import ComponentVersion
from app.services.issue_list import critical_issues_by_agent
from app.services.score import scores_by_agent
from app.services.spec import spec_state

_TYPES: dict[str, AgentType] = {
    "prompt": "single_prompt",
    "flow": "conversational_flow",
}


def agent_types(
    *,
    session: Session,
    agents: list[Agent],
    currents: dict[uuid.UUID, str] | None = None,
) -> dict[uuid.UUID, AgentType]:
    """Each agent's type: whether its current version links to a prompt or a flow in
    the catalogue. One query for every agent."""
    if currents is None:
        currents = crud.current_agent_versions(
            session=session, agent_ids=[a.id for a in agents]
        )
    wanted = {
        (a.id, a.platform_agent_id, currents[a.id])
        for a in agents
        if a.id in currents and a.platform_agent_id
    }
    if not wanted:
        return {}
    rows = session.exec(
        select(ComponentVersion).where(
            col(ComponentVersion.agent_id).in_([agent_id for agent_id, _, _ in wanted]),
            ComponentVersion.kind == "agent",
        )
    ).all()
    types: dict[uuid.UUID, AgentType] = {}
    for row in rows:
        if (row.agent_id, row.ref, row.version) not in wanted:
            continue
        for link in row.links or []:
            kind = _TYPES.get(link.get("kind", ""))
            if kind is not None:
                types[row.agent_id] = kind
                break
    return types


def live_since(
    *, session: Session, agent: Agent, version: str | None
) -> datetime | None:
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


def workspace_agents(
    *, session: Session, company_id: uuid.UUID, period: Period
) -> AgentListPublic:
    agents = crud.linked_agents(session=session, company_id=company_id)
    calls = calls_by_agent(
        session=session, company_id=company_id, since=period_start(period)
    )
    ids = [a.id for a in agents]
    currents = crud.current_agent_versions(session=session, agent_ids=ids)
    types = agent_types(session=session, agents=agents, currents=currents)
    specs = crud.latest_specs(session=session, agent_ids=ids)
    latency = agent_gap_percentiles(
        session=session, agent_ids=ids, since=period_start(period)
    )
    scores = scores_by_agent(session=session, company_id=company_id, period=period)
    critical = critical_issues_by_agent(
        session=session, company_id=company_id, period=period
    )
    rows = [
        AgentListItemPublic(
            id=agent.id,
            name=agent.name,
            platform=agent.platform,
            type=types.get(agent.id),
            calls=calls.get(agent.id, 0),
            score=scores.get(agent.id, (None, None))[0],
            score_change=scores.get(agent.id, (None, None))[1],
            critical_issues=critical.get(agent.id, 0),
            latency_p50=latency[agent.id].p50 if agent.id in latency else None,
            latency_p95=latency[agent.id].p95 if agent.id in latency else None,
            live_version=currents.get(agent.id),
            live_since=live_since(
                session=session, agent=agent, version=currents.get(agent.id)
            ),
            spec=spec_state(specs.get(agent.id), currents.get(agent.id)),
        )
        for agent in agents
    ]
    # Lowest score first, so the agents that need attention come first (Dmytro,
    # 2026-11-19); agents without a score after, most calls first.
    rows.sort(
        key=lambda r: (
            r.score is None,
            r.score if r.score is not None else 0,
            -r.calls,
            r.name.lower(),
        )
    )
    return AgentListPublic(
        data=rows,
        period=period,
    )
