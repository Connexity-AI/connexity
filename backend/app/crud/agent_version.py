import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from app.models import Agent, AgentVersion
from app.models.agent import validate_agent_mode_requirements
from app.models.enums import AgentVersionStatus
from app.services.agent_tool_definitions import normalize_and_validate_agent_tools

_VERSIONABLE_FIELDS = (
    "mode",
    "endpoint_url",
    "system_prompt",
    "tools",
    "agent_model",
    "agent_provider",
    "agent_temperature",
)


def next_published_version_number(*, session: Session, agent_id: uuid.UUID) -> int:
    m = session.exec(
        select(func.max(AgentVersion.version)).where(
            AgentVersion.agent_id == agent_id,
            AgentVersion.status == AgentVersionStatus.PUBLISHED,
            col(AgentVersion.version).is_not(None),
        )
    ).one()
    return int(m or 0) + 1


def _deactivate_published_active(*, session: Session, agent_id: uuid.UUID) -> None:
    session.execute(
        sa_update(AgentVersion)
        .where(
            AgentVersion.agent_id == agent_id,
            col(AgentVersion.is_active).is_(True),
        )
        .values(is_active=False)
    )


def get_active_published_version(
    *, session: Session, agent_id: uuid.UUID
) -> AgentVersion | None:
    statement = select(AgentVersion).where(
        AgentVersion.agent_id == agent_id,
        AgentVersion.status == AgentVersionStatus.PUBLISHED,
        col(AgentVersion.is_active).is_(True),
    )
    return session.exec(statement).first()


def active_published_versions_by_agent_ids(
    *, session: Session, agent_ids: list[uuid.UUID]
) -> dict[uuid.UUID, AgentVersion]:
    if not agent_ids:
        return {}
    rows = session.exec(
        select(AgentVersion).where(
            col(AgentVersion.agent_id).in_(agent_ids),
            AgentVersion.status == AgentVersionStatus.PUBLISHED,
            col(AgentVersion.is_active).is_(True),
        )
    ).all()
    return {row.agent_id: row for row in rows}


def build_version_row(
    *,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    version: int | None,
    status: AgentVersionStatus,
    source: Agent | AgentVersion,
    created_by: uuid.UUID | None,
    is_active: bool = False,
    version_name: str | None = None,
    version_description: str | None = None,
) -> AgentVersion:
    return AgentVersion(
        agent_id=agent_id,
        company_id=company_id,
        version=version,
        status=status,
        mode=source.mode,
        endpoint_url=source.endpoint_url,
        system_prompt=source.system_prompt,
        tools=source.tools,
        agent_model=source.agent_model,
        agent_provider=source.agent_provider,
        agent_temperature=source.agent_temperature,
        is_active=is_active,
        version_name=version_name,
        version_description=version_description,
        created_by=created_by,
    )


def create_initial_version(
    *,
    session: Session,
    agent: Agent,
    company_id: uuid.UUID,
    created_by: uuid.UUID | None,
) -> AgentVersion:
    row = build_version_row(
        agent_id=agent.id,
        company_id=company_id,
        version=1,
        status=AgentVersionStatus.PUBLISHED,
        source=agent,
        created_by=created_by,
        is_active=True,
        version_name=None,
        version_description=None,
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
    base_filter = (
        AgentVersion.agent_id == agent_id,
        AgentVersion.status == AgentVersionStatus.PUBLISHED,
    )
    count_statement = select(func.count()).select_from(AgentVersion).where(*base_filter)
    count = session.exec(count_statement).one()
    statement = (
        select(AgentVersion)
        .where(*base_filter)
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
    version_name: str | None,
    version_description: str | None,
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

    new_version_num = next_published_version_number(session=session, agent_id=locked.id)
    _deactivate_published_active(session=session, agent_id=locked.id)

    session.execute(
        sa_update(Agent)
        .where(Agent.id == locked.id)
        .values(
            mode=target.mode,
            endpoint_url=target.endpoint_url,
            system_prompt=target.system_prompt,
            tools=target.tools,
            agent_model=target.agent_model,
            agent_provider=target.agent_provider,
            agent_temperature=target.agent_temperature,
            updated_at=datetime.now(UTC),
        )
    )
    session.flush()
    session.refresh(locked)

    new_row = build_version_row(
        agent_id=locked.id,
        company_id=locked.company_id,
        version=new_version_num,
        status=AgentVersionStatus.PUBLISHED,
        source=locked,
        created_by=created_by,
        is_active=True,
        version_name=version_name,
        version_description=version_description,
    )
    session.add(new_row)

    draft = get_draft(session=session, agent_id=locked.id)
    if draft is not None:
        for field in _VERSIONABLE_FIELDS:
            setattr(draft, field, getattr(target, field))
        session.add(draft)
    else:
        new_draft = build_version_row(
            agent_id=locked.id,
            company_id=locked.company_id,
            version=None,
            status=AgentVersionStatus.DRAFT,
            source=target,
            created_by=created_by,
            is_active=False,
            version_name=None,
            version_description=None,
        )
        session.add(new_draft)
        locked.has_draft = True
        session.add(locked)

    session.commit()
    session.refresh(locked)
    session.refresh(new_row)
    return locked, new_row


def get_draft(*, session: Session, agent_id: uuid.UUID) -> AgentVersion | None:
    statement = select(AgentVersion).where(
        AgentVersion.agent_id == agent_id,
        AgentVersion.status == AgentVersionStatus.DRAFT,
    )
    return session.exec(statement).first()


def create_or_update_draft(
    *,
    session: Session,
    agent: Agent,
    draft_data: dict[str, object],
    created_by: uuid.UUID | None,
) -> AgentVersion:
    if "tools" in draft_data and draft_data["tools"] is not None:
        draft_data["tools"] = normalize_and_validate_agent_tools(
            draft_data["tools"],  # type: ignore[arg-type]
        )

    locked = session.exec(
        select(Agent).where(Agent.id == agent.id).with_for_update()
    ).first()
    if locked is None:
        msg = "Agent not found"
        raise ValueError(msg)

    existing_draft = get_draft(session=session, agent_id=locked.id)

    if existing_draft is not None:
        for key, value in draft_data.items():
            setattr(existing_draft, key, value)
        session.add(existing_draft)
        session.commit()
        session.refresh(existing_draft)
        return existing_draft

    draft = build_version_row(
        agent_id=locked.id,
        company_id=locked.company_id,
        version=None,
        status=AgentVersionStatus.DRAFT,
        source=locked,
        created_by=created_by,
        is_active=False,
        version_name=None,
        version_description=None,
    )
    for key, value in draft_data.items():
        setattr(draft, key, value)
    session.add(draft)

    locked.has_draft = True
    session.add(locked)

    session.commit()
    session.refresh(draft)
    return draft


def publish_draft(
    *,
    session: Session,
    agent: Agent,
    version_name: str | None,
    version_description: str | None,
    created_by: uuid.UUID | None,
) -> AgentVersion:
    locked = session.exec(
        select(Agent).where(Agent.id == agent.id).with_for_update()
    ).first()
    if locked is None:
        msg = "Agent not found"
        raise ValueError(msg)

    draft = get_draft(session=session, agent_id=locked.id)
    if draft is None:
        msg = "No draft to publish"
        raise ValueError(msg)

    validate_agent_mode_requirements(
        mode=draft.mode,
        endpoint_url=draft.endpoint_url,
        system_prompt=draft.system_prompt,
        agent_model=draft.agent_model,
    )

    new_version = next_published_version_number(session=session, agent_id=locked.id)
    _deactivate_published_active(session=session, agent_id=locked.id)

    published_row = build_version_row(
        agent_id=locked.id,
        company_id=locked.company_id,
        version=new_version,
        status=AgentVersionStatus.PUBLISHED,
        source=draft,
        created_by=created_by,
        is_active=True,
        version_name=version_name,
        version_description=version_description,
    )
    session.add(published_row)

    session.execute(
        sa_update(Agent)
        .where(Agent.id == locked.id)
        .values(
            has_draft=False,
            mode=draft.mode,
            endpoint_url=draft.endpoint_url,
            system_prompt=draft.system_prompt,
            tools=draft.tools,
            agent_model=draft.agent_model,
            agent_provider=draft.agent_provider,
            agent_temperature=draft.agent_temperature,
            updated_at=datetime.now(UTC),
        )
    )

    session.commit()
    session.refresh(published_row)
    session.refresh(locked)
    return published_row


def discard_draft(*, session: Session, agent: Agent) -> None:
    locked = session.exec(
        select(Agent).where(Agent.id == agent.id).with_for_update()
    ).first()
    if locked is None:
        msg = "Agent not found"
        raise ValueError(msg)

    draft = get_draft(session=session, agent_id=locked.id)
    if draft is not None:
        session.delete(draft)

    locked.has_draft = False
    session.add(locked)
    session.commit()
