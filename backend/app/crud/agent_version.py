import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from app.models import Agent, AgentVersion
from app.models.agent import validate_agent_mode_requirements


def build_version_row(
    *,
    agent_id: uuid.UUID,
    version: int,
    source: Agent | AgentVersion,
    change_description: str | None,
    created_by: uuid.UUID | None,
) -> AgentVersion:
    return AgentVersion(
        agent_id=agent_id,
        version=version,
        mode=source.mode,
        endpoint_url=source.endpoint_url,
        system_prompt=source.system_prompt,
        tools=source.tools,
        agent_model=source.agent_model,
        agent_provider=source.agent_provider,
        change_description=change_description,
        created_by=created_by,
    )


def create_initial_version(
    *,
    session: Session,
    agent: Agent,
    created_by: uuid.UUID | None,
) -> AgentVersion:
    row = build_version_row(
        agent_id=agent.id,
        version=1,
        source=agent,
        change_description=None,
        created_by=created_by,
    )
    session.add(row)
    session.flush()
    return row


def get_current_version_row(
    *, session: Session, agent_id: uuid.UUID, version: int
) -> AgentVersion | None:
    statement = select(AgentVersion).where(
        AgentVersion.agent_id == agent_id,
        AgentVersion.version == version,
    )
    return session.exec(statement).first()


def list_versions(
    *, session: Session, agent_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> tuple[list[AgentVersion], int]:
    count_statement = (
        select(func.count())
        .select_from(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(col(AgentVersion.version).desc())
        .offset(skip)
        .limit(limit)
    )
    items = list(session.exec(statement).all())
    return items, count


def get_version(
    *, session: Session, agent_id: uuid.UUID, version: int
) -> AgentVersion | None:
    return get_current_version_row(session=session, agent_id=agent_id, version=version)


def rollback_to_version(
    *,
    session: Session,
    db_agent: Agent,
    target_version: int,
    change_description: str | None,
    created_by: uuid.UUID | None,
) -> tuple[Agent, AgentVersion]:
    locked = session.exec(
        select(Agent).where(Agent.id == db_agent.id).with_for_update()
    ).first()
    if locked is None:
        msg = "Agent not found"
        raise ValueError(msg)

    target = get_version(session=session, agent_id=locked.id, version=target_version)
    if target is None:
        msg = f"Agent version {target_version} not found"
        raise ValueError(msg)

    validate_agent_mode_requirements(
        mode=target.mode,
        endpoint_url=target.endpoint_url,
        system_prompt=target.system_prompt,
        agent_model=target.agent_model,
    )

    session.execute(
        sa_update(Agent)
        .where(Agent.id == locked.id)
        .values(
            version=Agent.version + 1,
            mode=target.mode,
            endpoint_url=target.endpoint_url,
            system_prompt=target.system_prompt,
            tools=target.tools,
            agent_model=target.agent_model,
            agent_provider=target.agent_provider,
            updated_at=datetime.now(UTC),
        )
    )
    session.flush()
    session.refresh(locked)
    new_row = build_version_row(
        agent_id=locked.id,
        version=locked.version,
        source=locked,
        change_description=change_description,
        created_by=created_by,
    )
    session.add(new_row)
    session.commit()
    session.refresh(locked)
    session.refresh(new_row)
    return locked, new_row
