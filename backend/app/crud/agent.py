import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy import update as sa_update
from sqlmodel import Session, select

from app.crud import agent_version as agent_version_crud
from app.models import Agent, AgentCreate, AgentUpdate
from app.models.agent import validate_agent_mode_requirements

_VERSIONABLE_FIELDS = frozenset(
    {
        "mode",
        "endpoint_url",
        "system_prompt",
        "tools",
        "agent_model",
        "agent_provider",
    }
)


def _values_equal(a: object, b: object) -> bool:
    return a == b


def _versionable_fields_changed(*, before: Agent, patch: dict[str, object]) -> bool:
    for key in _VERSIONABLE_FIELDS:
        if key not in patch:
            continue
        if not _values_equal(getattr(before, key), patch[key]):
            return True
    return False


def create_agent(
    *, session: Session, agent_in: AgentCreate, created_by: uuid.UUID | None = None
) -> Agent:
    db_obj = Agent.model_validate(agent_in)
    db_obj.version = 1
    session.add(db_obj)
    session.flush()
    agent_version_crud.create_initial_version(
        session=session, agent=db_obj, created_by=created_by
    )
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


def update_agent(
    *,
    session: Session,
    db_agent: Agent,
    agent_in: AgentUpdate,
    created_by: uuid.UUID | None = None,
) -> Agent:
    locked = session.exec(
        select(Agent).where(Agent.id == db_agent.id).with_for_update()
    ).first()
    if locked is None:
        msg = "Agent not found"
        raise ValueError(msg)

    update_data = agent_in.model_dump(exclude_unset=True)
    change_description = update_data.pop("change_description", None)

    if not update_data:
        return locked

    if not _versionable_fields_changed(before=locked, patch=update_data):
        locked.sqlmodel_update(update_data)
        validate_agent_mode_requirements(
            mode=locked.mode,
            endpoint_url=locked.endpoint_url,
            system_prompt=locked.system_prompt,
            agent_model=locked.agent_model,
        )
        session.add(locked)
        session.commit()
        session.refresh(locked)
        return locked

    working = locked.model_copy(update=update_data)
    validate_agent_mode_requirements(
        mode=working.mode,
        endpoint_url=working.endpoint_url,
        system_prompt=working.system_prompt,
        agent_model=working.agent_model,
    )

    session.execute(
        sa_update(Agent)
        .where(Agent.id == locked.id)
        .values(
            version=Agent.version + 1,
            name=working.name,
            description=working.description,
            mode=working.mode,
            endpoint_url=working.endpoint_url,
            system_prompt=working.system_prompt,
            tools=working.tools,
            agent_model=working.agent_model,
            agent_provider=working.agent_provider,
            agent_metadata=working.agent_metadata,
            updated_at=datetime.now(UTC),
        )
    )
    session.flush()
    session.refresh(locked)
    new_row = agent_version_crud.build_version_row(
        agent_id=locked.id,
        version=locked.version,
        source=locked,
        change_description=change_description,
        created_by=created_by,
    )
    session.add(new_row)
    session.commit()
    session.refresh(locked)
    return locked


def delete_agent(*, session: Session, db_agent: Agent) -> None:
    session.delete(db_agent)
    session.commit()
