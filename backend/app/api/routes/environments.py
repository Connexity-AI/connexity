import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_user, get_owned_agent
from app.models import (
    Environment,
    EnvironmentCreate,
    EnvironmentPublic,
    EnvironmentsPublic,
    Message,
)

router = APIRouter(
    prefix="/environments",
    tags=["environments"],
    dependencies=[Depends(get_current_user)],
)


def _to_public(env: Environment, integration_name: str) -> EnvironmentPublic:
    return EnvironmentPublic(
        id=env.id,
        name=env.name,
        platform=env.platform,
        agent_id=env.agent_id,
        integration_id=env.integration_id,
        integration_name=integration_name,
        platform_agent_id=env.platform_agent_id,
        platform_agent_name=env.platform_agent_name,
        created_at=env.created_at,
    )


@router.post("/", response_model=EnvironmentPublic)
def create_environment(
    session: SessionDep,
    current_user: CurrentUser,
    environment_in: EnvironmentCreate,
) -> EnvironmentPublic:
    get_owned_agent(
        agent_id=environment_in.agent_id,
        session=session,
        current_user=current_user,
    )
    integration = crud.get_integration(
        session=session,
        integration_id=environment_in.integration_id,
        user_id=current_user.id,
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    db_obj = crud.create_environment(session=session, data=environment_in)
    return _to_public(db_obj, integration.name)


@router.get("/", response_model=EnvironmentsPublic)
def list_environments(
    session: SessionDep,
    current_user: CurrentUser,
    agent_id: uuid.UUID = Query(...),
) -> EnvironmentsPublic:
    get_owned_agent(agent_id=agent_id, session=session, current_user=current_user)
    rows = crud.list_environments_by_agent(session=session, agent_id=agent_id)
    return EnvironmentsPublic(
        data=[_to_public(env, name) for env, name in rows],
        count=len(rows),
    )


@router.delete("/{environment_id}", response_model=Message)
def delete_environment(
    session: SessionDep,
    current_user: CurrentUser,
    environment_id: uuid.UUID,
) -> Message:
    env = crud.get_environment(session=session, environment_id=environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    get_owned_agent(agent_id=env.agent_id, session=session, current_user=current_user)
    integration = crud.get_integration(
        session=session,
        integration_id=env.integration_id,
        user_id=current_user.id,
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Environment not found")
    crud.delete_environment(session=session, db_environment=env)
    return Message(message="Environment deleted successfully")
