import uuid

from cryptography.fernet import InvalidToken
from sqlmodel import Session, col, select

from app.core.encryption import decrypt, key_fingerprint
from app.models import Agent
from app.models.enums import AgentMode, IntegrationProvider, Platform
from app.models.integration import Integration


def get_agent(
    *, session: Session, agent_id: uuid.UUID, company_id: uuid.UUID | None = None
) -> Agent | None:
    agent = session.get(Agent, agent_id)
    if agent is None:
        return None
    if company_id is not None and agent.company_id != company_id:
        return None
    return agent


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
    platform agent in this workspace is returned as it is. No prompt is imported:
    Connexity observes the agent, it does not build it.
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
