"""The Dashboard of the workspace open on the web (`services/dashboard.py`)."""

import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentCompany, SessionDep
from app.models.agent import Agent
from app.models.dashboard import DashboardPublic
from app.services.dashboard import dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardPublic)
def read_dashboard(
    session: SessionDep,
    company_id: CurrentCompany,
    period: Literal["7d", "30d", "90d"] = "30d",
    agent_id: uuid.UUID | None = Query(default=None),
) -> DashboardPublic:
    """Where the workspace stands, for all its agents or one, over the period."""
    if agent_id is not None:
        agent = session.get(Agent, agent_id)
        if agent is None or agent.company_id != company_id:
            raise HTTPException(status_code=404, detail="Agent not found")
    return dashboard(
        session=session,
        company_id=company_id,
        period=period,
        agent_id=agent_id,
    )
