"""The Agents page and `list_agents`' type and calls (plan
`plans/2026-11-14-agents-page.md`)."""

import uuid
from datetime import datetime

from sqlmodel import Session, col, func, select

from app import crud
from app.crud.issue_list import calls_by_agent, period_start
from app.models.agent import Agent
from app.models.agent_list import (
    AgentListItemPublic,
    AgentListPublic,
    AgentType,
    Period,
)
from app.models.call_pull import CallPullAccount
from app.models.component_version import ComponentVersion
from app.models.enums import IntegrationProvider
from app.models.integration import Integration
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


def workspace_synced_at(*, session: Session, company_id: uuid.UUID) -> datetime | None:
    """When calls were last pulled for any of the workspace's Retell accounts."""
    return session.exec(
        select(func.max(col(CallPullAccount.last_pulled_at)))
        .join(
            Integration,
            col(Integration.key_fingerprint) == col(CallPullAccount.key_fingerprint),
        )
        .where(
            Integration.company_id == company_id,
            Integration.provider == IntegrationProvider.RETELL,
        )
    ).one()


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
    rows = [
        AgentListItemPublic(
            id=agent.id,
            name=agent.name,
            platform=agent.platform,
            type=types.get(agent.id),
            calls=calls.get(agent.id, 0),
            spec=spec_state(specs.get(agent.id), currents.get(agent.id)),
        )
        for agent in agents
    ]
    rows.sort(key=lambda r: (-r.calls, r.name.lower()))
    return AgentListPublic(
        data=rows,
        period=period,
        synced_at=workspace_synced_at(session=session, company_id=company_id),
    )
