import uuid

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models.environment import Environment, EnvironmentCreate
from app.models.integration import Integration


def create_environment(*, session: Session, data: EnvironmentCreate) -> Environment:
    db_obj = Environment(
        name=data.name,
        platform=data.platform,
        agent_id=data.agent_id,
        integration_id=data.integration_id,
        platform_agent_id=data.platform_agent_id,
        platform_agent_name=data.platform_agent_name,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_environment(
    *, session: Session, environment_id: uuid.UUID
) -> Environment | None:
    return session.get(Environment, environment_id)


def list_environments_by_agent(
    *, session: Session, agent_id: uuid.UUID
) -> list[tuple[Environment, str]]:
    statement = (
        select(Environment, Integration.name)
        .join(Integration, Environment.integration_id == Integration.id)
        .where(Environment.agent_id == agent_id)
        .order_by(col(Environment.created_at).desc())
    )
    return list(session.exec(statement).all())


def delete_environment(*, session: Session, db_environment: Environment) -> None:
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
