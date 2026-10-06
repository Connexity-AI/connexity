import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.models import (
    Agent,
    Environment,
    EnvironmentCreate,
    EnvironmentPublic,
    EnvironmentsPublic,
    EnvironmentUpdate,
    Message,
)
from app.models.enums import Platform
from app.models.environment import validate_environment_platform_fields

router = APIRouter(
    prefix="/environments",
    tags=["environments"],
    dependencies=[Depends(get_current_user)],
)


def _apply_agent_platform_to_environment_create(
    agent: Agent, environment_in: EnvironmentCreate
) -> EnvironmentCreate:
    if agent.platform in (Platform.RETELL, Platform.VAPI, Platform.ELEVENLABS):
        if agent.integration_id is None or not (agent.platform_agent_id or "").strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    "Agent is missing integration or provider agent binding; "
                    "fix the agent before creating environments"
                ),
            )
        data = environment_in.model_dump()
        data["platform"] = agent.platform
        data["endpoint_url"] = None
        return EnvironmentCreate.model_validate(data)
    if agent.platform == Platform.WEBHOOK:
        data = environment_in.model_dump()
        data["platform"] = Platform.WEBHOOK
        return EnvironmentCreate.model_validate(data)
    return environment_in


def _apply_agent_platform_to_environment_update(
    agent: Agent, _env: Environment, environment_in: EnvironmentUpdate
) -> EnvironmentUpdate:
    body_dump = environment_in.model_dump(exclude_unset=True)
    if agent.platform in (Platform.RETELL, Platform.VAPI, Platform.ELEVENLABS):
        if agent.integration_id is None or not (agent.platform_agent_id or "").strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    "Agent is missing integration or provider agent binding; "
                    "fix the agent before updating environments"
                ),
            )
        body_dump["platform"] = agent.platform
        body_dump["endpoint_url"] = None
        return EnvironmentUpdate.model_validate(body_dump)
    if agent.platform == Platform.WEBHOOK:
        body_dump["platform"] = Platform.WEBHOOK
        return EnvironmentUpdate.model_validate(body_dump)
    return environment_in


def _to_public(env: Environment, integration_name: str | None) -> EnvironmentPublic:
    return EnvironmentPublic(
        id=env.id,
        name=env.name,
        platform=env.platform,
        agent_id=env.agent_id,
        integration_name=integration_name,
        endpoint_url=env.endpoint_url,
        created_at=env.created_at,
    )


def _get_environment_integration_name(
    session: SessionDep,
    *,
    platform: Platform,
    integration_id: uuid.UUID | None,
    company_id: uuid.UUID,
) -> str | None:
    if platform not in {Platform.RETELL, Platform.VAPI, Platform.ELEVENLABS}:
        return None
    if integration_id is None:
        raise HTTPException(status_code=422, detail="Integration is required")
    integration = crud.get_integration(
        session=session, integration_id=integration_id, company_id=company_id
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration.name


@router.post("/", response_model=EnvironmentPublic)
def create_environment(
    session: SessionDep,
    company_id: CurrentCompany,
    environment_in: EnvironmentCreate,
) -> EnvironmentPublic:
    agent = crud.get_agent(
        session=session, agent_id=environment_in.agent_id, company_id=company_id
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    environment_in = _apply_agent_platform_to_environment_create(agent, environment_in)
    integration_name = _get_environment_integration_name(
        session=session,
        platform=environment_in.platform,
        integration_id=agent.integration_id,
        company_id=company_id,
    )
    db_obj = crud.create_environment(
        session=session, data=environment_in, company_id=company_id
    )
    return _to_public(db_obj, integration_name)


@router.get("/", response_model=EnvironmentsPublic)
def list_environments(
    session: SessionDep,
    company_id: CurrentCompany,
    agent_id: uuid.UUID = Query(...),
) -> EnvironmentsPublic:
    agent = crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    rows = crud.list_environments_by_agent(session=session, agent_id=agent_id)
    integration_name = _get_environment_integration_name(
        session=session,
        platform=agent.platform,
        integration_id=agent.integration_id,
        company_id=company_id,
    )
    return EnvironmentsPublic(
        data=[_to_public(env, integration_name) for env in rows],
        count=len(rows),
    )


@router.patch("/{environment_id}", response_model=EnvironmentPublic)
def update_environment(
    session: SessionDep,
    company_id: CurrentCompany,
    environment_id: uuid.UUID,
    environment_in: EnvironmentUpdate,
) -> EnvironmentPublic:
    env = crud.get_environment(
        session=session, environment_id=environment_id, company_id=company_id
    )
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    agent = crud.get_agent(
        session=session, agent_id=env.agent_id, company_id=company_id
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    environment_in = _apply_agent_platform_to_environment_update(
        agent, env, environment_in
    )

    update_data = environment_in.model_dump(exclude_unset=True)
    platform = update_data.get("platform", env.platform)
    endpoint_url = update_data.get("endpoint_url", env.endpoint_url)

    try:
        validate_environment_platform_fields(
            platform=platform,
            endpoint_url=endpoint_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    integration_name = _get_environment_integration_name(
        session=session,
        platform=platform,
        integration_id=agent.integration_id,
        company_id=company_id,
    )
    updated = crud.update_environment(
        session=session,
        db_environment=env,
        data=environment_in,
    )
    return _to_public(updated, integration_name)


@router.delete("/{environment_id}", response_model=Message)
def delete_environment(
    session: SessionDep,
    company_id: CurrentCompany,
    environment_id: uuid.UUID,
) -> Message:
    env = crud.get_environment(
        session=session, environment_id=environment_id, company_id=company_id
    )
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    crud.delete_environment(session=session, db_environment=env)
    return Message(message="Environment deleted successfully")
