import uuid
from typing import Any

from cryptography.fernet import InvalidToken
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.encryption import decrypt, key_fingerprint
from app.crud import agent_version as agent_version_crud
from app.models import (
    Agent,
    AgentCreate,
    AgentCreateDraft,
    AgentLastEvalSummary,
    AgentUpdate,
    AggregateMetrics,
    Run,
)
from app.models.enums import (
    AgentMode,
    AgentVersionStatus,
    IntegrationProvider,
    Platform,
    RunStatus,
)
from app.models.imported_platform_config import ImportedPlatformConfig
from app.models.integration import Integration
from app.services.agent_tool_definitions import normalize_and_validate_agent_tools

_VERSIONABLE_FIELDS = frozenset(
    {
        "mode",
        "endpoint_url",
        "system_prompt",
        "tools",
        "agent_model",
        "agent_provider",
        "agent_temperature",
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
    *,
    session: Session,
    agent_in: AgentCreate,
    company_id: uuid.UUID,
    created_by: uuid.UUID | None = None,
) -> Agent:
    data = agent_in.model_dump()
    if data.get("tools") is not None:
        data["tools"] = normalize_and_validate_agent_tools(data["tools"])
    data["company_id"] = company_id
    db_obj = Agent.model_validate(data)
    db_obj.created_by = created_by
    session.add(db_obj)
    session.flush()
    agent_version_crud.create_initial_version(
        session=session,
        agent=db_obj,
        company_id=company_id,
        created_by=created_by,
    )
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_draft_agent(
    *,
    session: Session,
    body: AgentCreateDraft,
    company_id: uuid.UUID,
    created_by: uuid.UUID | None = None,
    imported: ImportedPlatformConfig | None = None,
) -> Agent:
    name = body.name.strip() if body.name else "Untitled Agent"
    prompt_type = body.prompt_type

    if imported is not None:
        tools_norm: list[dict[str, Any]] | None = None
        if imported.tools:
            tools_norm = normalize_and_validate_agent_tools(imported.tools)
        db_obj = Agent(
            name=name,
            mode=AgentMode.PLATFORM,
            has_draft=False,
            company_id=company_id,
            created_by=created_by,
            platform=body.platform,
            prompt_type=prompt_type,
            integration_id=body.integration_id,
            platform_agent_id=body.platform_agent_id,
            platform_agent_name=body.platform_agent_name,
            system_prompt=imported.system_prompt,
            tools=tools_norm,
            agent_model=imported.agent_model,
            agent_provider=imported.agent_provider,
            agent_temperature=imported.agent_temperature,
        )
        session.add(db_obj)
        session.flush()
        agent_version_crud.create_initial_version(
            session=session,
            agent=db_obj,
            company_id=company_id,
            created_by=created_by,
        )
        session.commit()
        session.refresh(db_obj)
        return db_obj

    integration_id = (
        body.integration_id if body.platform not in (None, Platform.WEBHOOK) else None
    )
    platform_agent_id = (
        body.platform_agent_id
        if body.platform not in (None, Platform.WEBHOOK)
        else None
    )
    platform_agent_name = (
        body.platform_agent_name
        if body.platform not in (None, Platform.WEBHOOK)
        else None
    )

    # A provider agent whose config could not be imported still runs on the
    # provider's engine, so it gets a published version like any other. Only
    # agents with no provider behind them start as an unpublished draft.
    is_provider_agent = integration_id is not None and platform_agent_id is not None

    db_obj = Agent(
        name=name,
        mode=AgentMode.PLATFORM,
        has_draft=not is_provider_agent,
        company_id=company_id,
        created_by=created_by,
        platform=body.platform,
        prompt_type=prompt_type,
        integration_id=integration_id,
        platform_agent_id=platform_agent_id,
        platform_agent_name=platform_agent_name,
    )
    session.add(db_obj)
    session.flush()

    if is_provider_agent:
        agent_version_crud.create_initial_version(
            session=session,
            agent=db_obj,
            company_id=company_id,
            created_by=created_by,
        )
        session.commit()
        session.refresh(db_obj)
        return db_obj

    from app.models import AgentVersion

    draft = AgentVersion(
        agent_id=db_obj.id,
        company_id=company_id,
        version=None,
        status=AgentVersionStatus.DRAFT,
        mode=AgentMode.PLATFORM,
        created_by=created_by,
    )
    session.add(draft)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_agent(
    *, session: Session, agent_id: uuid.UUID, company_id: uuid.UUID | None = None
) -> Agent | None:
    agent = session.get(Agent, agent_id)
    if agent is None:
        return None
    if company_id is not None and agent.company_id != company_id:
        return None
    return agent


def list_agents(
    *,
    session: Session,
    company_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Agent], int]:
    count = session.exec(
        select(func.count()).select_from(Agent).where(Agent.company_id == company_id)
    ).one()
    items = list(
        session.exec(
            select(Agent)
            .where(Agent.company_id == company_id)
            .order_by(col(Agent.updated_at).desc())
            .offset(skip)
            .limit(limit)
        ).all()
    )
    return items, count


def add_platform_agent(
    *,
    session: Session,
    company_id: uuid.UUID,
    integration: Integration,
    platform: Platform,
    platform_agent_id: str,
    name: str,
    platform_agent_name: str | None,
    created_by: uuid.UUID,
) -> tuple[Agent, bool]:
    """Add an agent observed on a voice platform, linked to the workspace's connection.

    Returns the agent and whether it was new. An agent already linked to the same
    platform agent in this workspace is returned as it is. No prompt is imported and no
    1.x draft version is made: Connexity observes the agent, it does not build it.
    """
    existing = session.exec(
        select(Agent).where(
            Agent.company_id == company_id,
            Agent.platform == platform,
            Agent.platform_agent_id == platform_agent_id,
        )
    ).first()
    if existing is not None:
        return existing, False
    agent = Agent(
        company_id=company_id,
        name=name,
        mode=AgentMode.PLATFORM,
        platform=platform,
        integration_id=integration.id,
        platform_agent_id=platform_agent_id,
        platform_agent_name=platform_agent_name,
        created_by=created_by,
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent, True


def fill_key_fingerprints(*, session: Session) -> None:
    """Give a fingerprint to connections stored before fingerprints existed.

    Decrypts only those. A key stored under another encryption key cannot be read and
    keeps no fingerprint: it belongs to no account Connexity can reach.
    """
    missing = session.exec(
        select(Integration).where(col(Integration.key_fingerprint).is_(None))
    ).all()
    for integration in missing:
        try:
            integration.key_fingerprint = key_fingerprint(
                decrypt(integration.encrypted_api_key)
            )
        except InvalidToken:
            continue
        session.add(integration)
    if missing:
        session.commit()


def retell_agents_for_account(
    *,
    session: Session,
    fingerprint: str,
    platform_agent_id: str | None = None,
) -> list[Agent]:
    """The added Retell agents of one Retell account, in every workspace.

    A Retell account may be connected in several workspaces (one per client), and each
    may have added the same agent: those connections hold the same key, so the same
    fingerprint. With ``platform_agent_id``, only that Retell agent's copies.
    """
    query = (
        select(Agent)
        .join(Integration, col(Integration.id) == col(Agent.integration_id))
        .where(
            Integration.provider == IntegrationProvider.RETELL,
            Integration.key_fingerprint == fingerprint,
            Agent.platform == Platform.RETELL,
            col(Agent.platform_agent_id).is_not(None),
        )
        .order_by(col(Agent.created_at))
    )
    if platform_agent_id is not None:
        query = query.where(Agent.platform_agent_id == platform_agent_id)
    return list(session.exec(query).all())


def search_agents(
    *,
    session: Session,
    company_id: uuid.UUID,
    query: str | None = None,
    offset: int = 0,
    limit: int = 25,
) -> tuple[list[Agent], bool]:
    """A page of the company's agents, newest first, optionally matching a name.

    Returns the page and whether another page follows.
    """
    statement = select(Agent).where(Agent.company_id == company_id)
    if query:
        statement = statement.where(col(Agent.name).icontains(query, autoescape=True))
    rows = list(
        session.exec(
            statement.order_by(col(Agent.created_at).desc(), col(Agent.id).desc())
            .offset(offset)
            .limit(limit + 1)
        ).all()
    )
    return rows[:limit], len(rows) > limit


def latest_completed_eval_summaries_by_agent(
    *, session: Session, company_id: uuid.UUID, agent_ids: list[uuid.UUID]
) -> dict[uuid.UUID, AgentLastEvalSummary]:
    if not agent_ids:
        return {}

    summaries: dict[uuid.UUID, AgentLastEvalSummary] = {}
    completed_runs = session.exec(
        select(Run)
        .where(
            col(Run.status) == RunStatus.COMPLETED,
            col(Run.agent_id).in_(agent_ids),
            Run.company_id == company_id,
        )
        .order_by(col(Run.created_at).desc())
    ).all()

    for run in completed_runs:
        if run.agent_id in summaries:
            continue
        aggregate_metrics = (
            AggregateMetrics.model_validate(run.aggregate_metrics)
            if run.aggregate_metrics is not None
            else None
        )
        summaries[run.agent_id] = AgentLastEvalSummary(
            run_id=run.id,
            created_at=run.created_at,
            aggregate_metrics=aggregate_metrics,
        )
    return summaries


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
