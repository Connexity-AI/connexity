import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_user, get_owned_agent
from app.core.encryption import decrypt
from app.models import (
    Deployment,
    DeploymentCreate,
    DeploymentPublic,
    DeploymentsPublic,
    Environment,
    EnvironmentCreate,
    EnvironmentPublic,
    EnvironmentsPublic,
    Message,
)
from app.services.retell import (
    RetellAgentVersion,
    deploy_retell_agent,
    list_retell_agent_versions,
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
        current_version_number=env.current_version_number,
        current_version_name=env.current_version_name,
        current_deployed_at=env.current_deployed_at,
        created_at=env.created_at,
    )


def _deployment_to_public(
    deployment: Deployment, environment_name: str
) -> DeploymentPublic:
    return DeploymentPublic(
        id=deployment.id,
        environment_id=deployment.environment_id,
        environment_name=environment_name,
        agent_id=deployment.agent_id,
        agent_version=deployment.agent_version,
        retell_version_name=deployment.retell_version_name,
        status=deployment.status,
        error_message=deployment.error_message,
        deployed_by_user_id=deployment.deployed_by_user_id,
        deployed_by_name=deployment.deployed_by_name,
        deployed_at=deployment.deployed_at,
    )


@router.post("/", response_model=EnvironmentPublic)
def create_environment(
    session: SessionDep,
    environment_in: EnvironmentCreate,
) -> EnvironmentPublic:
    agent = crud.get_agent(session=session, agent_id=environment_in.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    integration = crud.get_integration(
        session=session,
        integration_id=environment_in.integration_id,
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    db_obj = crud.create_environment(session=session, data=environment_in)
    return _to_public(db_obj, integration.name)


@router.get("/", response_model=EnvironmentsPublic)
def list_environments(
    session: SessionDep,
    agent_id: uuid.UUID = Query(...),
) -> EnvironmentsPublic:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    rows = crud.list_environments_by_agent(session=session, agent_id=agent_id)
    return EnvironmentsPublic(
        data=[_to_public(env, name) for env, name in rows],
        count=len(rows),
    )


@router.delete("/{environment_id}", response_model=Message)
def delete_environment(
    session: SessionDep,
    environment_id: uuid.UUID,
) -> Message:
    env = crud.get_environment(session=session, environment_id=environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    integration = crud.get_integration(
        session=session,
        integration_id=env.integration_id,
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Environment not found")
    crud.delete_environment(session=session, db_environment=env)
    return Message(message="Environment deleted successfully")


@router.post("/{environment_id}/deploy", response_model=DeploymentPublic)
async def deploy_environment(
    session: SessionDep,
    current_user: CurrentUser,
    environment_id: uuid.UUID,
    body: DeploymentCreate,
) -> DeploymentPublic:
    env = crud.get_environment(session=session, environment_id=environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    get_owned_agent(agent_id=env.agent_id, session=session, current_user=current_user)

    integration = crud.get_integration(
        session=session,
        integration_id=env.integration_id,
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    version_row = crud.get_agent_version(
        session=session, agent_id=env.agent_id, version=body.agent_version
    )
    if version_row is None:
        raise HTTPException(status_code=404, detail="Agent version not found")

    deployment = crud.create_pending_deployment(
        session=session,
        environment_id=env.id,
        agent_id=env.agent_id,
        agent_version=body.agent_version,
        deployed_by_user_id=current_user.id,
        deployed_by_name=current_user.full_name or current_user.email,
    )

    api_key = decrypt(integration.encrypted_api_key)
    connexity_label = f"Connexity Agent v{body.agent_version}"
    notes = (version_row.change_description or "").strip()
    combined_description = f"{connexity_label} — {notes}" if notes else connexity_label

    result = await deploy_retell_agent(
        api_key=api_key,
        retell_agent_id=env.platform_agent_id,
        system_prompt=version_row.system_prompt,
        agent_model=version_row.agent_model,
        agent_temperature=version_row.agent_temperature,
        tools=version_row.tools,
        change_description=combined_description,
    )

    if result.success:
        deployment = crud.mark_deployment_succeeded(
            session=session,
            deployment=deployment,
            retell_version_name=result.retell_version_name,
        )
    else:
        deployment = crud.mark_deployment_failed(
            session=session,
            deployment=deployment,
            error_message=result.error_message or "Unknown Retell error",
        )

    return _deployment_to_public(deployment, env.name)


@router.get(
    "/{environment_id}/retell-versions",
    response_model=list[RetellAgentVersion],
)
async def list_environment_retell_versions(
    session: SessionDep,
    current_user: CurrentUser,
    environment_id: uuid.UUID,
) -> list[RetellAgentVersion]:
    env = crud.get_environment(session=session, environment_id=environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    get_owned_agent(agent_id=env.agent_id, session=session, current_user=current_user)

    integration = crud.get_integration(
        session=session,
        integration_id=env.integration_id,
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    api_key = decrypt(integration.encrypted_api_key)
    versions = await list_retell_agent_versions(
        api_key=api_key, retell_agent_id=env.platform_agent_id
    )
    published = [v for v in versions if v.is_published]
    published.sort(key=lambda v: v.version, reverse=True)
    return published


@router.get("/deployments", response_model=DeploymentsPublic)
def list_agent_deployments(
    session: SessionDep,
    agent_id: uuid.UUID = Query(...),
) -> DeploymentsPublic:
    if not crud.get_agent(session=session, agent_id=agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    rows = crud.list_deployments_for_agent(session=session, agent_id=agent_id)
    return DeploymentsPublic(
        data=[_deployment_to_public(d, name) for d, name in rows],
        count=len(rows),
    )


@router.get("/{environment_id}/deployments", response_model=DeploymentsPublic)
def list_environment_deployments(
    session: SessionDep,
    environment_id: uuid.UUID,
) -> DeploymentsPublic:
    env = crud.get_environment(session=session, environment_id=environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    rows = crud.list_deployments_for_environment(
        session=session, environment_id=environment_id
    )
    return DeploymentsPublic(
        data=[_deployment_to_public(d, env.name) for d in rows],
        count=len(rows),
    )
