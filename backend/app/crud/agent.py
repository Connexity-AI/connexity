import uuid

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Agent, AgentCreate, AgentUpdate


def create_agent(*, session: Session, agent_in: AgentCreate) -> Agent:
    db_obj = Agent.model_validate(agent_in)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_agent(*, session: Session, agent_id: uuid.UUID) -> Agent | None:
    return session.get(Agent, agent_id)


def list_agents(
    *, session: Session, skip: int = 0, limit: int = 100
) -> tuple[list[Agent], int]:
    count = session.exec(select(func.count()).select_from(Agent)).one()
    items = list(session.exec(select(Agent).offset(skip).limit(limit)).all())
    return items, count


def update_agent(*, session: Session, db_agent: Agent, agent_in: AgentUpdate) -> Agent:
    update_data = agent_in.model_dump(exclude_unset=True)
    db_agent.sqlmodel_update(update_data)
    session.add(db_agent)
    session.commit()
    session.refresh(db_agent)
    return db_agent


def delete_agent(*, session: Session, db_agent: Agent) -> None:
    session.delete(db_agent)
    session.commit()
