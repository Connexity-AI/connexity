"""The versions of each component that have served an agent's calls."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.models import (
    Agent,
    ComponentVersionPublic,
    ComponentVersionSummary,
    VersionResolveResult,
)
from app.services.component_versions import resolve_agent_versions

router = APIRouter(
    prefix="/agents/{agent_id}",
    tags=["component-versions"],
    dependencies=[Depends(get_current_user)],
)


def _agent_or_404(
    session: SessionDep, company_id: uuid.UUID, agent_id: uuid.UUID
) -> Agent:
    agent = crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/component-versions", response_model=list[ComponentVersionSummary])
def list_agent_component_versions(
    session: SessionDep,
    company_id: CurrentCompany,
    agent_id: uuid.UUID,
    kind: str | None = Query(default=None, max_length=64),
) -> list[ComponentVersionSummary]:
    """Every version seen for the agent, newest first within each kind. No content."""
    _agent_or_404(session, company_id, agent_id)
    return [
        ComponentVersionSummary.model_validate(row, from_attributes=True)
        for row in crud.list_component_versions(
            session=session, agent_id=agent_id, kind=kind
        )
    ]


@router.get(
    "/component-versions/{component_version_id}",
    response_model=ComponentVersionPublic,
)
def get_agent_component_version(
    session: SessionDep,
    company_id: CurrentCompany,
    agent_id: uuid.UUID,
    component_version_id: uuid.UUID,
) -> ComponentVersionPublic:
    """One version with its content, credentials masked."""
    _agent_or_404(session, company_id, agent_id)
    row = crud.get_component_version_by_id(
        session=session, component_version_id=component_version_id, agent_id=agent_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Component version not found")
    return ComponentVersionPublic.model_validate(row, from_attributes=True)


@router.post("/versions/resolve", response_model=VersionResolveResult)
async def resolve_agent_call_versions(
    session: SessionDep, company_id: CurrentCompany, agent_id: uuid.UUID
) -> VersionResolveResult:
    """Work out what served the agent's stored calls that do not say yet.

    Reads each agent version from the provider once. Safe to run again.
    """
    agent = _agent_or_404(session, company_id, agent_id)
    return await resolve_agent_versions(session=session, agent=agent)
