"""The Agents page: the open workspace's agents (plan `plans/2026-11-14-agents-page.md`).

Included before the 1.x agents router, whose `/agents/{agent_id}` would otherwise
catch `/agents/list`.
"""

from typing import Literal

from fastapi import APIRouter, Depends

from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.models.agent_list import AgentListPublic
from app.services.agent_list import workspace_agents

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
