"""An agent's Tests tab, read only (plan `plans/2026-11-17-tests-tab.md`).

The assistant writes and runs scenarios through MCP; the web app only reads them.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app import crud
from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.models.test_run import TestsTabPublic
from app.services.tests_tab import tests_tab

router = APIRouter(tags=["tests"], dependencies=[Depends(get_current_user)])


@router.get("/agents/{agent_id}/tests", response_model=TestsTabPublic)
def get_agent_tests(
    session: SessionDep, company_id: CurrentCompany, agent_id: uuid.UUID
) -> TestsTabPublic:
    """The newest tested version's verdict, what failed with its simulated calls,
    coverage of the latest spec, every rule's totals, and the scenarios and sets."""
    agent = crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return tests_tab(session=session, agent=agent)
