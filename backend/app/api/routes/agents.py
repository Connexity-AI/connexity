import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.models import (
    Agent,
    AgentCreate,
    AgentPublic,
    AgentRollbackRequest,
    AgentsPublic,
    AgentUpdate,
    AgentVersionDiff,
    AgentVersionPublic,
    AgentVersionsPublic,
    Message,
)
from app.services.diff import compute_agent_version_diff

router = APIRouter(
    prefix="/agents", tags=["agents"], dependencies=[Depends(get_current_user)]
)


@router.post("/", response_model=AgentPublic)
def create_agent(
    session: SessionDep,
    current_user: CurrentUser,
    agent_in: AgentCreate,
) -> Agent:
    return crud.create_agent(
        session=session, agent_in=agent_in, created_by=current_user.id
    )


@router.get("/", response_model=AgentsPublic)
def list_agents(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> AgentsPublic:
    items, count = crud.list_agents(session=session, skip=skip, limit=limit)
    return AgentsPublic(data=items, count=count)  # type: ignore[arg-type]


@router.get("/{agent_id}/versions/diff", response_model=AgentVersionDiff)
def diff_agent_versions(
    session: SessionDep,
    agent_id: uuid.UUID,
    from_version: int = Query(ge=1, description="Earlier version number"),
    to_version: int = Query(ge=1, description="Later version number"),
) -> AgentVersionDiff:
    if from_version == to_version:
        raise HTTPException(
            status_code=400,
            detail="from_version and to_version must be different",
        )
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    row_from = crud.get_agent_version(
        session=session, agent_id=agent_id, version=from_version
    )
    row_to = crud.get_agent_version(
        session=session, agent_id=agent_id, version=to_version
    )
    if row_from is None or row_to is None:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    return compute_agent_version_diff(
        from_version_num=from_version,
        to_version_num=to_version,
        old=row_from,
        new=row_to,
    )


@router.get("/{agent_id}/versions/{version}", response_model=AgentVersionPublic)
def read_agent_version(
    session: SessionDep,
    agent_id: uuid.UUID,
    version: int,
) -> AgentVersionPublic:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    row = crud.get_agent_version(session=session, agent_id=agent_id, version=version)
    if row is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return AgentVersionPublic.model_validate(row)


@router.get("/{agent_id}/versions", response_model=AgentVersionsPublic)
def list_agent_versions(
    session: SessionDep,
    agent_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> AgentVersionsPublic:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    items, count = crud.list_agent_versions(
        session=session, agent_id=agent_id, skip=skip, limit=limit
    )
    return AgentVersionsPublic(
        data=[AgentVersionPublic.model_validate(v) for v in items],
        count=count,
    )


@router.post("/{agent_id}/rollback", response_model=AgentVersionPublic)
def rollback_agent(
    session: SessionDep,
    current_user: CurrentUser,
    agent_id: uuid.UUID,
    body: AgentRollbackRequest,
) -> AgentVersionPublic:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        _agent, new_row = crud.rollback_agent_version(
            session=session,
            db_agent=agent,
            target_version=body.version,
            change_description=body.change_description,
            created_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return AgentVersionPublic.model_validate(new_row)


@router.get("/{agent_id}", response_model=AgentPublic)
def get_agent(session: SessionDep, agent_id: uuid.UUID) -> Agent:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentPublic)
def update_agent(
    session: SessionDep,
    current_user: CurrentUser,
    agent_id: uuid.UUID,
    agent_in: AgentUpdate,
) -> Agent:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        return crud.update_agent(
            session=session,
            db_agent=agent,
            agent_in=agent_in,
            created_by=current_user.id,
        )
    except ValueError as e:
        detail = str(e)
        if detail == "Agent not found":
            raise HTTPException(status_code=404, detail=detail) from e
        raise HTTPException(status_code=422, detail=detail) from e


@router.delete("/{agent_id}", response_model=Message)
def delete_agent(session: SessionDep, agent_id: uuid.UUID) -> Message:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    crud.delete_agent(session=session, db_agent=agent)
    return Message(message="Agent deleted successfully")
