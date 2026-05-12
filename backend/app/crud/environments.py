import uuid

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models.deployment import Deployment
from app.models.environment import Environment, EnvironmentCreate, EnvironmentUpdate
from app.models.integration import Integration


def create_environment(*, session: Session, data: EnvironmentCreate) -> Environment:
    db_obj = Environment(
        name=data.name,
        platform=data.platform,
        agent_id=data.agent_id,
        integration_id=data.integration_id,
        platform_agent_id=data.platform_agent_id,
        platform_agent_name=data.platform_agent_name,
        endpoint_url=data.endpoint_url,
        eval_gate_eval_config_id=data.eval_gate_eval_config_id,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_environment(
    *, session: Session, environment_id: uuid.UUID
) -> Environment | None:
    return session.get(Environment, environment_id)


def update_environment(
    *, session: Session, db_environment: Environment, data: EnvironmentUpdate
) -> Environment:
    update_data = data.model_dump(exclude_unset=True)
    db_environment.sqlmodel_update(update_data)
    session.add(db_environment)
    session.commit()
    session.refresh(db_environment)
    return db_environment


def list_environments_by_agent(
    *, session: Session, agent_id: uuid.UUID
) -> list[tuple[Environment, str | None]]:
    statement = (
        select(Environment, Integration.name)
        .outerjoin(Integration, Environment.integration_id == Integration.id)
        .where(Environment.agent_id == agent_id)
        .order_by(col(Environment.created_at).desc())
    )
    return list(session.exec(statement).all())


def delete_environment(*, session: Session, db_environment: Environment) -> None:
    deployments = session.exec(
        select(Deployment).where(Deployment.environment_id == db_environment.id)
    ).all()
    for d in deployments:
        session.delete(d)
    session.delete(db_environment)
    session.commit()


def count_environments_for_integration(
    *, session: Session, integration_id: uuid.UUID
) -> int:
    statement = (
        select(func.count())
        .select_from(Environment)
        .where(Environment.integration_id == integration_id)
    )
    return session.exec(statement).one()
