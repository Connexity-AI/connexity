import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from app.models import Agent, AgentVersion
from app.models.agent import validate_agent_mode_requirements
from app.models.enums import AgentVersionStatus

_VERSIONABLE_FIELDS = (
    "mode",
    "endpoint_url",
    "system_prompt",
    "tools",
    "agent_model",
    "agent_provider",
)


def build_version_row(
    *,
    agent_id: uuid.UUID,
    version: int | None,
    status: AgentVersionStatus,
    source: Agent | AgentVersion,
    change_description: str | None,
    created_by: uuid.UUID | None,
) -> AgentVersion:
    return AgentVersion(
        agent_id=agent_id,
        version=version,
        status=status,
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
        status=AgentVersionStatus.PUBLISHED,
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
        status=AgentVersionStatus.PUBLISHED,
        source=locked,
        change_description=change_description,
        created_by=created_by,
    )
    session.add(new_row)
    session.commit()
    session.refresh(locked)
    session.refresh(new_row)
    return locked, new_row


# ── Draft/Publish lifecycle ──────────────────────────────────────────


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
    locked = session.exec(
        select(Agent).where(Agent.id == agent.id).with_for_update()
    ).first()
    if locked is None:
        msg = "Agent not found"
        raise ValueError(msg)

    existing_draft = get_draft(session=session, agent_id=locked.id)

    if existing_draft is not None:
        # Merge provided fields into existing draft
        for key, value in draft_data.items():
            setattr(existing_draft, key, value)
        session.add(existing_draft)
        session.commit()
        session.refresh(existing_draft)
        return existing_draft

    # Create new draft from current published config + provided changes
    draft = build_version_row(
        agent_id=locked.id,
        version=None,
        status=AgentVersionStatus.DRAFT,
        source=locked,
        change_description=None,
        created_by=created_by,
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
    change_description: str | None,
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

    new_version = locked.version + 1

    # Promote draft → published
    draft.version = new_version
    draft.status = AgentVersionStatus.PUBLISHED
    if change_description is not None:
        draft.change_description = change_description
    if created_by is not None:
        draft.created_by = created_by
    session.add(draft)

    # Update agent's live config from draft
    session.execute(
        sa_update(Agent)
        .where(Agent.id == locked.id)
        .values(
            version=new_version,
            has_draft=False,
            mode=draft.mode,
            endpoint_url=draft.endpoint_url,
            system_prompt=draft.system_prompt,
            tools=draft.tools,
            agent_model=draft.agent_model,
            agent_provider=draft.agent_provider,
            updated_at=datetime.now(UTC),
        )
    )

    session.commit()
    session.refresh(draft)
    session.refresh(locked)
    return draft


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
