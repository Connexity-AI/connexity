"""An agent's spec, read-only, for the Spec tab (plan `plans/2026-11-14-spec-api.md`).

The assistant writes specs through MCP (`write_spec`); the web app only reads them.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.models.spec import SpecPublic
from app.services.spec import spec_answer

router = APIRouter(tags=["spec"], dependencies=[Depends(get_current_user)])


@router.get("/agents/{agent_id}/spec", response_model=SpecPublic)
def get_agent_spec(
    session: SessionDep,
    company_id: CurrentCompany,
    agent_id: uuid.UUID,
    version: int | None = Query(default=None, ge=1),
) -> SpecPublic:
    """The agent's spec, latest or ``version``, rules grouped by the fixed categories."""
    agent = crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    answer = spec_answer(session=session, agent=agent, version=version)
    if answer is None:
        raise HTTPException(status_code=404, detail="Spec version not found")
    return answer
