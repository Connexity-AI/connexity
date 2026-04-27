import uuid
from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.models.deployment import Deployment
from app.models.enums import DeploymentStatus
from app.models.environment import Environment


def create_pending_deployment(
    *,
    session: Session,
    environment_id: uuid.UUID,
    agent_id: uuid.UUID,
    agent_version: int,
    deployed_by_user_id: uuid.UUID | None,
    deployed_by_name: str | None,
) -> Deployment:
    db_obj = Deployment(
        environment_id=environment_id,
        agent_id=agent_id,
        agent_version=agent_version,
        status=DeploymentStatus.PENDING,
        deployed_by_user_id=deployed_by_user_id,
        deployed_by_name=deployed_by_name,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def mark_deployment_succeeded(
    *,
    session: Session,
    deployment: Deployment,
    retell_version_name: str | None,
) -> Deployment:
    deployment.status = DeploymentStatus.DEPLOYED
    deployment.retell_version_name = retell_version_name
    deployment.error_message = None
    session.add(deployment)

    env = session.get(Environment, deployment.environment_id)
    if env is not None:
        env.current_version_number = deployment.agent_version
        env.current_version_name = retell_version_name
        env.current_deployed_at = datetime.now(UTC)
        session.add(env)

    session.commit()
    session.refresh(deployment)
    return deployment


def mark_deployment_failed(
    *,
    session: Session,
    deployment: Deployment,
    error_message: str,
) -> Deployment:
    deployment.status = DeploymentStatus.FAILED
    deployment.error_message = error_message
    session.add(deployment)
    session.commit()
    session.refresh(deployment)
    return deployment


def list_deployments_for_environment(
    *, session: Session, environment_id: uuid.UUID
) -> list[Deployment]:
    statement = (
        select(Deployment)
        .where(Deployment.environment_id == environment_id)
        .order_by(col(Deployment.deployed_at).desc())
    )
    return list(session.exec(statement).all())
