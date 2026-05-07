import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.core.config import settings
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
    EnvironmentUpdate,
    Message,
    WebhookDeployPayload,
    WebhookEval,
)
from app.models.agent_version import AgentVersion
from app.models.enums import Platform
from app.models.environment import validate_environment_platform_fields
from app.models.schemas import AggregateMetrics
from app.models.user import User
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


def _version_notes_for_retell(version_row: AgentVersion) -> str:
    parts: list[str] = []
    if version_row.version_name and version_row.version_name.strip():
        parts.append(version_row.version_name.strip())
    if version_row.version_description and version_row.version_description.strip():
        parts.append(version_row.version_description.strip())
    return "\n".join(parts)


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


def _user_display_name(user: User | None) -> str | None:
    if user is None:
        return None
    return user.full_name or str(user.email)


def _deployment_to_public(
    deployment: Deployment,
    environment_name: str,
    deployed_by_display_name: str | None,
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
        deployed_by_display_name=deployed_by_display_name,
        deployed_at=deployment.deployed_at,
    )


def _deployments_to_public_list(
    session: SessionDep,
    rows: list[tuple[Deployment, str]],
) -> list[DeploymentPublic]:
    user_ids = [
        d.deployed_by_user_id for d, _ in rows if d.deployed_by_user_id is not None
    ]
    unique_ids = list(dict.fromkeys(user_ids))
    users_map = crud.list_users_by_ids(session=session, user_ids=unique_ids)
    return [
        _deployment_to_public(
            d,
            name,
            _user_display_name(users_map.get(d.deployed_by_user_id))
            if d.deployed_by_user_id
            else None,
        )
        for d, name in rows
    ]


def _validate_gate_config(
    session: SessionDep, *, agent_id: uuid.UUID, eval_config_id: uuid.UUID | None
) -> None:
    if eval_config_id is None:
        return
    gate_cfg = crud.get_eval_config(session=session, eval_config_id=eval_config_id)
    if not gate_cfg or gate_cfg.agent_id != agent_id:
        raise HTTPException(
            status_code=422,
            detail="Eval gate config not found or belongs to a different agent",
        )


def _get_environment_integration_name(
    session: SessionDep, *, platform: Platform, integration_id: uuid.UUID | None
) -> str | None:
    if platform != Platform.RETELL:
        return None
    if integration_id is None:
        raise HTTPException(status_code=422, detail="Integration is required")
    integration = crud.get_integration(session=session, integration_id=integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration.name


def _get_eval_payload_for_gate(
    session: SessionDep,
    *,
    agent_id: uuid.UUID,
    agent_version: int,
    eval_config_id: uuid.UUID | None,
    enforce_gate: bool,
) -> WebhookEval:
    if eval_config_id is None:
        return WebhookEval()

    gate_cfg = crud.get_eval_config(session=session, eval_config_id=eval_config_id)
    config_name = gate_cfg.name if gate_cfg is not None else None

    def _results_link(run_id: uuid.UUID) -> str | None:
        if not settings.SITE_URL:
            return None
        base_url = settings.SITE_URL.rstrip("/")
        return f"{base_url}/agents/{agent_id}/evals/eval-runs/{run_id}"

    gate_run = crud.get_latest_completed_run_for_version(
        session=session,
        agent_id=agent_id,
        eval_config_id=eval_config_id,
        agent_version=agent_version,
    )
    if gate_run is None:
        if enforce_gate:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Eval gate: no completed eval run for this version on the "
                    "gated config. Run the eval first."
                ),
            )
        return WebhookEval(
            config_id=str(eval_config_id),
            config_name=config_name,
        )

    gate_metrics = (
        AggregateMetrics.model_validate(gate_run.aggregate_metrics)
        if gate_run.aggregate_metrics
        else None
    )
    passed = (
        gate_metrics is not None
        and gate_metrics.metrics_passed
        and gate_metrics.cases_passed
    )
    if enforce_gate and not passed:
        raise HTTPException(
            status_code=409,
            detail=(
                "Eval gate: latest run for this version did not pass the "
                "gated config's thresholds."
            ),
        )

    return WebhookEval(
        config_id=str(eval_config_id),
        config_name=config_name,
        run_at=gate_run.completed_at or gate_run.updated_at,
        passed=passed,
        metrics_score=(
            gate_metrics.weighted_metrics_score_pct
            if gate_metrics is not None
            else None
        ),
        metrics_pass_threshold=(
            gate_metrics.metrics_pass_threshold if gate_metrics is not None else None
        ),
        cases_passed=gate_metrics.passed_count if gate_metrics is not None else None,
        cases_total=gate_metrics.total_executions if gate_metrics is not None else None,
        cases_pass_threshold=(
            gate_metrics.cases_pass_threshold if gate_metrics is not None else None
        ),
        results_link=_results_link(gate_run.id),
    )


@router.post("/", response_model=EnvironmentPublic)
def create_environment(
    session: SessionDep,
    environment_in: EnvironmentCreate,
) -> EnvironmentPublic:
    agent = crud.get_agent(session=session, agent_id=environment_in.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    integration_name = _get_environment_integration_name(
        session=session,
        platform=environment_in.platform,
        integration_id=environment_in.integration_id,
    )
    _validate_gate_config(
        session=session,
        agent_id=environment_in.agent_id,
        eval_config_id=environment_in.eval_gate_eval_config_id,
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


@router.get("/webhook-payload-preview", response_model=WebhookDeployPayload)
def get_webhook_payload_preview(
    session: SessionDep,
    current_user: CurrentUser,
    agent_id: uuid.UUID = Query(...),
    environment_name: str = Query(..., min_length=1, max_length=255),
    eval_gate_eval_config_id: uuid.UUID | None = Query(default=None),
) -> WebhookDeployPayload:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    version_row = crud.get_active_agent_version(session=session, agent_id=agent_id)
    if version_row is None or version_row.version is None:
        raise HTTPException(status_code=404, detail="Agent version not found")

    safe_environment_name = environment_name.strip()
    if not safe_environment_name:
        raise HTTPException(status_code=422, detail="Environment name is required")

    _validate_gate_config(
        session=session,
        agent_id=agent_id,
        eval_config_id=eval_gate_eval_config_id,
    )
    eval_payload = _get_eval_payload_for_gate(
        session=session,
        agent_id=agent_id,
        agent_version=version_row.version,
        eval_config_id=eval_gate_eval_config_id,
        enforce_gate=False,
    )
    payload = build_webhook_payload(
        agent=agent,
        environment=Environment(
            name=safe_environment_name,
            platform=Platform.WEBHOOK,
            agent_id=agent_id,
        ),
        version_row=version_row,
        deployed_by=current_user.full_name or current_user.email,
        eval_gate=eval_payload,
    )
    return payload


@router.patch("/{environment_id}", response_model=EnvironmentPublic)
def update_environment(
    session: SessionDep,
    environment_id: uuid.UUID,
    environment_in: EnvironmentUpdate,
) -> EnvironmentPublic:
    env = crud.get_environment(session=session, environment_id=environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    update_data = environment_in.model_dump(exclude_unset=True)
    platform = update_data.get("platform", env.platform)
    integration_id = update_data.get("integration_id", env.integration_id)
    platform_agent_id = update_data.get("platform_agent_id", env.platform_agent_id)
    endpoint_url = update_data.get("endpoint_url", env.endpoint_url)
    platform_changed = "platform" in update_data and platform != env.platform

    try:
        validate_environment_platform_fields(
            platform=platform,
            integration_id=integration_id,
            platform_agent_id=platform_agent_id,
            endpoint_url=endpoint_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    integration_name = _get_environment_integration_name(
        session=session,
        platform=platform,
        integration_id=integration_id,
    )
    _validate_gate_config(
        session=session,
        agent_id=env.agent_id,
        eval_config_id=update_data.get(
            "eval_gate_eval_config_id", env.eval_gate_eval_config_id
        ),
    )

    updated = crud.update_environment(
        session=session,
        db_environment=env,
        data=environment_in,
    )
    if platform_changed:
        updated.current_version_number = None
        updated.current_version_name = None
        updated.current_deployed_at = None
        session.add(updated)
        session.commit()
        session.refresh(updated)
    return _to_public(updated, integration_name)


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

    eval_payload = _get_eval_payload_for_gate(
        session=session,
        agent_id=env.agent_id,
        agent_version=body.agent_version,
        eval_config_id=env.eval_gate_eval_config_id,
        enforce_gate=True,
    )

    deployment = crud.create_pending_deployment(
        session=session,
        environment_id=env.id,
        agent_id=env.agent_id,
        agent_version=body.agent_version,
        deployed_by_user_id=current_user.id,
    )

    deployed_version_name = version_row.version_name
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
        notes = _version_notes_for_retell(version_row).strip()
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
            version_description=combined_description,
        )
        deployed_version_name = result.retell_version_name
    elif env.platform == Platform.WEBHOOK:
        if env.endpoint_url is None:
            raise HTTPException(
                status_code=422,
                detail="Webhook environment is missing endpoint URL",
            )
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

    deployer_user = None
    if deployment.deployed_by_user_id is not None:
        umap = crud.list_users_by_ids(
            session=session, user_ids=[deployment.deployed_by_user_id]
        )
        deployer_user = umap.get(deployment.deployed_by_user_id)

    return _deployment_to_public(
        deployment,
        env.name,
        _user_display_name(deployer_user),
    )


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
        data=_deployments_to_public_list(session, rows),
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
    rows_with_name = [(d, env.name) for d in rows]
    return DeploymentsPublic(
        data=_deployments_to_public_list(session, rows_with_name),
        count=len(rows),
    )
