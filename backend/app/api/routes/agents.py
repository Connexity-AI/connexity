import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import (
    Agent,
    AgentCreate,
    AgentPublic,
    AgentsPublic,
    AgentUpdate,
    Message,
)

router = APIRouter(
    prefix="/agents", tags=["agents"], dependencies=[Depends(get_current_user)]
)


@router.post("/", response_model=AgentPublic)
def create_agent(session: SessionDep, agent_in: AgentCreate) -> Agent:
    return crud.create_agent(session=session, agent_in=agent_in)


@router.get("/", response_model=AgentsPublic)
def list_agents(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> AgentsPublic:
    items, count = crud.list_agents(session=session, skip=skip, limit=limit)
    return AgentsPublic(data=items, count=count)  # type: ignore[arg-type]


@router.get("/{agent_id}", response_model=AgentPublic)
def get_agent(session: SessionDep, agent_id: uuid.UUID) -> Agent:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentPublic)
def update_agent(
    session: SessionDep,
    agent_id: uuid.UUID,
    agent_in: AgentUpdate,
) -> Agent:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return crud.update_agent(session=session, db_agent=agent, agent_in=agent_in)


@router.delete("/{agent_id}", response_model=Message)
def delete_agent(session: SessionDep, agent_id: uuid.UUID) -> Message:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    crud.delete_agent(session=session, db_agent=agent)
    return Message(message="Agent deleted successfully")
