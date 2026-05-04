import uuid

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.crud import agent_version as agent_version_crud
from app.models import Agent, AgentCreate, AgentGuidelinesPublic, AgentUpdate
from app.models.enums import AgentMode, AgentVersionStatus
from app.services.agent_tool_definitions import normalize_and_validate_agent_tools

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
    data = agent_in.model_dump()
    if data.get("tools") is not None:
        data["tools"] = normalize_and_validate_agent_tools(data["tools"])
    db_obj = Agent.model_validate(data)
    db_obj.version = 1
    db_obj.created_by = created_by
    session.add(db_obj)
    session.flush()
    agent_version_crud.create_initial_version(
        session=session, agent=db_obj, created_by=created_by
    )
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_draft_agent(
    *,
    session: Session,
    name: str = "Untitled Agent",
    created_by: uuid.UUID | None = None,
) -> Agent:
    db_obj = Agent(
        name=name,
        mode=AgentMode.PLATFORM,
        version=0,
        has_draft=True,
        created_by=created_by,
    )
    session.add(db_obj)
    session.flush()

    from app.models import AgentVersion

    draft = AgentVersion(
        agent_id=db_obj.id,
        version=None,
        status=AgentVersionStatus.DRAFT,
        mode=AgentMode.PLATFORM,
        created_by=created_by,
    )
    session.add(draft)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_agent(*, session: Session, agent_id: uuid.UUID) -> Agent | None:
    return session.get(Agent, agent_id)


def list_agents(
    *, session: Session, skip: int = 0, limit: int = 100
) -> tuple[list[Agent], int]:
    count = session.exec(select(func.count()).select_from(Agent)).one()
    items = list(
        session.exec(
            select(Agent)
            .order_by(col(Agent.updated_at).desc())
            .offset(skip)
            .limit(limit)
        ).all()
    )
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
    update_data.pop("change_description", None)

    if not update_data:
        return locked

    # Split into identity vs versionable changes
    identity_data = {
        k: v for k, v in update_data.items() if k not in _VERSIONABLE_FIELDS
    }
    versionable_data = {
        k: v for k, v in update_data.items() if k in _VERSIONABLE_FIELDS
    }

    has_versionable_change = bool(versionable_data) and _versionable_fields_changed(
        before=locked, patch=versionable_data
    )

    # Apply identity changes directly to agent
    if identity_data:
        locked.sqlmodel_update(identity_data)
        session.add(locked)

    # Send versionable changes to draft
    if has_versionable_change:
        agent_version_crud.create_or_update_draft(
            session=session,
            agent=locked,
            draft_data=versionable_data,
            created_by=created_by,
        )

    session.commit()
    session.refresh(locked)
    return locked


def delete_agent(*, session: Session, db_agent: Agent) -> None:
    session.delete(db_agent)
    session.commit()


def agent_guidelines_public(*, agent: Agent) -> AgentGuidelinesPublic:
    """Build API response: full default text when unset, plus whether custom text is stored."""
    from app.services.prompt_editor.agent_prompt import get_effective_guidelines

    stored = agent.editor_guidelines
    is_default = stored is None or not stored.strip()
    effective = get_effective_guidelines(stored)
    return AgentGuidelinesPublic(guidelines=effective, is_default=is_default)


def set_agent_editor_guidelines(
    *, session: Session, db_agent: Agent, guidelines: str | None
) -> Agent:
    """Persist editor guidelines; None or whitespace-only clears to built-in default."""
    if guidelines is None or not guidelines.strip():
        db_agent.editor_guidelines = None
    else:
        db_agent.editor_guidelines = guidelines.strip()
    session.add(db_agent)
    session.commit()
    session.refresh(db_agent)
    return db_agent
