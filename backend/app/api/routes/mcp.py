import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import McpCurrentUser, SessionDep, require_mcp_user
from app.models import (
    AgentDraftUpdate,
    AgentLatestPublishedVersionPublic,
    AgentPublic,
    AgentsPublic,
    AgentVersionPublic,
)

router = APIRouter(
    prefix="/mcp",
    tags=["mcp"],
    dependencies=[Depends(require_mcp_user)],
)


@router.get("/agents", response_model=AgentsPublic)
def list_agents(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> AgentsPublic:
    items, count = crud.list_agents(session=session, skip=skip, limit=limit)
    summaries_by_agent_id = crud.latest_completed_eval_summaries_by_agent(
        session=session, agent_ids=[agent.id for agent in items]
    )
    active_versions = crud.list_active_published_versions_by_agent_ids(
        session=session, agent_ids=[agent.id for agent in items]
    )
    data: list[AgentPublic] = []
    for agent in items:
        serialized = AgentPublic.model_validate(agent)
        serialized.last_eval = summaries_by_agent_id.get(agent.id)
        active = active_versions.get(agent.id)
        if active is not None and active.version is not None:
            serialized.latest_published_version = AgentLatestPublishedVersionPublic(
                version=active.version,
                version_name=active.version_name,
                version_description=active.version_description,
            )
        data.append(serialized)
    return AgentsPublic(data=data, count=count)


@router.get("/agents/{agent_id}/draft", response_model=AgentVersionPublic)
def get_draft(
    session: SessionDep,
    agent_id: uuid.UUID,
) -> AgentVersionPublic:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    draft = crud.get_agent_draft(session=session, agent_id=agent_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="No draft found")
    return AgentVersionPublic.model_validate(draft)


@router.put("/agents/{agent_id}/draft", response_model=AgentVersionPublic)
def upsert_draft(
    session: SessionDep,
    current_user: McpCurrentUser,
    agent_id: uuid.UUID,
    body: AgentDraftUpdate,
) -> AgentVersionPublic:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    draft_data = body.model_dump(exclude_unset=True)
    if not draft_data:
        raise HTTPException(status_code=422, detail="No fields provided")
    try:
        draft = crud.create_or_update_agent_draft(
            session=session,
            agent=agent,
            draft_data=draft_data,
            created_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return AgentVersionPublic.model_validate(draft)
