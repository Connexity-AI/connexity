import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_user
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
from app.models.enums import Platform
from app.models.schemas import AggregateMetrics
from app.services.retell import (
    RetellAgentVersion,
    deploy_retell_agent,
    list_retell_agent_versions,
)
from app.services.webhook_deploy import (
    build_webhook_payload,
    deliver_webhook_deployment,
)

router = APIRouter(
    prefix="/environments",
    tags=["environments"],
    dependencies=[Depends(get_current_user)],
)


def _to_public(env: Environment, integration_name: str | None) -> EnvironmentPublic:
    return EnvironmentPublic(
        id=env.id,
        name=env.name,
        platform=env.platform,
        agent_id=env.agent_id,
        integration_id=env.integration_id,
        integration_name=integration_name,
        platform_agent_id=env.platform_agent_id,
        platform_agent_name=env.platform_agent_name,
        endpoint_url=env.endpoint_url,
        current_version_number=env.current_version_number,
        current_version_name=env.current_version_name,
        current_deployed_at=env.current_deployed_at,
        eval_gate_eval_config_id=env.eval_gate_eval_config_id,
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
    integration_name: str | None = None
    if environment_in.platform == Platform.RETELL:
        integration_id = environment_in.integration_id
        if integration_id is None:
            raise HTTPException(status_code=422, detail="Integration is required")
        integration = crud.get_integration(
            session=session,
            integration_id=integration_id,
        )
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        integration_name = integration.name
    if environment_in.eval_gate_eval_config_id is not None:
        gate_cfg = crud.get_eval_config(
            session=session, eval_config_id=environment_in.eval_gate_eval_config_id
        )
        if not gate_cfg or gate_cfg.agent_id != environment_in.agent_id:
            raise HTTPException(
                status_code=422,
                detail="Eval gate config not found or belongs to a different agent",
            )
    db_obj = crud.create_environment(session=session, data=environment_in)
    return _to_public(db_obj, integration_name)


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
    if env.integration_id is not None:
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
    agent = crud.get_agent(session=session, agent_id=env.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    version_row = crud.get_agent_version(
        session=session, agent_id=env.agent_id, version=body.agent_version
    )
    if version_row is None:
        raise HTTPException(status_code=404, detail="Agent version not found")

    gate_run = None
    gate_metrics: AggregateMetrics | None = None
    if env.eval_gate_eval_config_id is not None:
        gate_run = crud.get_latest_completed_run_for_version(
            session=session,
            agent_id=env.agent_id,
            eval_config_id=env.eval_gate_eval_config_id,
            agent_version=body.agent_version,
        )
        if gate_run is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Eval gate: no completed eval run for this version on the "
                    "gated config. Run the eval first."
                ),
            )
        gate_metrics = (
            AggregateMetrics.model_validate(gate_run.aggregate_metrics)
            if gate_run.aggregate_metrics
            else None
        )
        if (
            gate_metrics is None
            or not gate_metrics.metrics_passed
            or not gate_metrics.cases_passed
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Eval gate: latest run for this version did not pass the "
                    "gated config's thresholds."
                ),
            )

    deployment = crud.create_pending_deployment(
        session=session,
        environment_id=env.id,
        agent_id=env.agent_id,
        agent_version=body.agent_version,
        deployed_by_user_id=current_user.id,
        deployed_by_name=current_user.full_name or current_user.email,
    )

    deployed_version_name = version_row.change_description
    if env.platform == Platform.RETELL:
        if env.integration_id is None or env.platform_agent_id is None:
            raise HTTPException(
                status_code=422,
                detail="Retell environment is missing integration or agent id",
            )
        integration = crud.get_integration(
            session=session,
            integration_id=env.integration_id,
        )
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        api_key = decrypt(integration.encrypted_api_key)
        connexity_label = f"Connexity Agent v{body.agent_version}"
        notes = (version_row.change_description or "").strip()
        combined_description = (
            f"{connexity_label} — {notes}" if notes else connexity_label
        )

        result = await deploy_retell_agent(
            api_key=api_key,
            retell_agent_id=env.platform_agent_id,
            system_prompt=version_row.system_prompt,
            agent_model=version_row.agent_model,
            agent_temperature=version_row.agent_temperature,
            tools=version_row.tools,
            change_description=combined_description,
        )
        deployed_version_name = result.retell_version_name
    elif env.platform == Platform.WEBHOOK:
        if env.endpoint_url is None:
            raise HTTPException(
                status_code=422,
                detail="Webhook environment is missing endpoint URL",
            )
        eval_payload = None
        if env.eval_gate_eval_config_id is not None and gate_run is not None:
            eval_payload = {
                "config_id": str(env.eval_gate_eval_config_id),
                "run_at": gate_run.completed_at or gate_run.updated_at,
                "passed": bool(
                    gate_metrics is not None
                    and gate_metrics.metrics_passed
                    and gate_metrics.cases_passed
                ),
                "metrics_score": (
                    gate_metrics.weighted_metrics_score_pct
                    if gate_metrics is not None
                    else None
                ),
                "metrics_pass_threshold": (
                    gate_metrics.metrics_pass_threshold
                    if gate_metrics is not None
                    else None
                ),
                "cases_passed": gate_metrics.passed_count if gate_metrics is not None else None,
                "cases_total": (
                    gate_metrics.total_executions if gate_metrics is not None else None
                ),
                "cases_pass_threshold": (
                    gate_metrics.cases_pass_threshold
                    if gate_metrics is not None
                    else None
                ),
            }
        payload = build_webhook_payload(
            agent=agent,
            environment=env,
            version_row=version_row,
            deployed_by=current_user.full_name or current_user.email,
            eval_gate=eval_payload,
        )
        result = await deliver_webhook_deployment(
            endpoint_url=env.endpoint_url,
            payload=payload,
        )
    else:
        raise HTTPException(status_code=422, detail="Unsupported environment platform")

    if result.success:
        deployment = crud.mark_deployment_succeeded(
            session=session,
            deployment=deployment,
            retell_version_name=deployed_version_name,
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
    environment_id: uuid.UUID,
) -> list[RetellAgentVersion]:
    env = crud.get_environment(session=session, environment_id=environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    if crud.get_agent(session=session, agent_id=env.agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if env.platform != Platform.RETELL:
        raise HTTPException(
            status_code=400,
            detail="Retell versions are only available for Retell environments",
        )
    if env.integration_id is None or env.platform_agent_id is None:
        raise HTTPException(
            status_code=422,
            detail="Retell environment is missing integration or agent id",
        )

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
