"""The Agents page: the open workspace's agents (plan `plans/2026-11-14-agents-page.md`).

Included before the 1.x agents router, whose `/agents/{agent_id}` would otherwise
catch `/agents/list`.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from app import crud
from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.models.agent_list import AgentListPublic
from app.models.agent_page import AgentPagePublic
from app.services.agent_list import workspace_agents
from app.services.agent_page import agent_page

router = APIRouter(tags=["agents"], dependencies=[Depends(get_current_user)])


@router.get("/agents/list", response_model=AgentListPublic)
def list_workspace_agents(
    session: SessionDep,
    company_id: CurrentCompany,
    period: Literal["7d", "30d", "90d"] = "30d",
) -> AgentListPublic:
    """The workspace's agents with their platform and type and calls in the period,
    most calls first, and when calls were last pulled."""
    return workspace_agents(session=session, company_id=company_id, period=period)


@router.get("/agents/{agent_id}/page", response_model=AgentPagePublic)
def get_agent_page(
    session: SessionDep,
    company_id: CurrentCompany,
    agent_id: uuid.UUID,
    period: Literal["7d", "30d", "90d"] = "30d",
) -> AgentPagePublic:
    """The agent page's Overview: the caption, tiles, details and latency over time
    with version marks, for the period."""
    agent = crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent_page(session=session, agent=agent, period=period)
