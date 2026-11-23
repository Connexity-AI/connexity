import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models import Agent, User
from app.models.agency import Agency
from app.models.company import Company
from app.models.enums import IntegrationProvider, Platform
from app.models.integration import Integration
from app.tests.utils.utils import AUTH_USER_EMAIL


def _resolve_company_id(session: Session, company_id: uuid.UUID | None) -> uuid.UUID:
    """Use the explicit company_id when given, otherwise resolve a stable default.

    Prefer the default auth test user's company so route tests reusing the same
    session see the data. Falls back to picking the first Company in the DB,
    creating one on the fly if there are none.
    """
    if company_id is not None:
        return company_id
    user = session.exec(select(User).where(User.email == AUTH_USER_EMAIL)).first()
    if user is not None:
        return user.company_id
    existing = session.exec(select(Company)).first()
    if existing is not None:
        return existing.id
    agency = Agency(name="Test agency")
    session.add(agency)
    session.flush()
    new_company = Company(agency_id=agency.id)
    session.add(new_company)
    session.commit()
    session.refresh(new_company)
    return new_company.id


def get_test_company_id(session: Session) -> uuid.UUID:
    """Public helper for tests that call ``crud`` directly and need a company_id."""
    return _resolve_company_id(session, None)


def create_test_agent(
    session: Session,
    *,
    company_id: uuid.UUID | None = None,
    name: str | None = None,
) -> Agent:
    cid = _resolve_company_id(session, company_id)
    agent = Agent(
        company_id=cid,
        name=name or f"test-agent-{uuid.uuid4().hex[:8]}",
        description="Test agent for automated tests",
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def create_agent_as(
    client: TestClient,
    cookies: dict[str, str],
    *,
    name: str | None = None,
    linked: bool = False,
) -> Agent:
    """An agent in the workspace the signed-in person has open. ``linked`` makes it
    an agent added from a voice platform, the kind the Agents list shows."""
    me = client.get(f"{settings.API_V1_STR}/users/me", cookies=cookies)
    assert me.status_code == 200, me.text
    company_id = uuid.UUID(me.json()["company_id"])
    with Session(engine) as session:
        agent = create_test_agent(session, company_id=company_id, name=name)
        if linked:
            integration = Integration(
                provider=IntegrationProvider.RETELL,
                name="Production",
                company_id=company_id,
                encrypted_api_key="encrypted",
                masked_api_key="key_****",
            )
            session.add(integration)
            session.flush()
            agent.platform = Platform.RETELL
            agent.integration_id = integration.id
            agent.platform_agent_id = f"agent_{uuid.uuid4().hex[:8]}"
            session.add(agent)
            session.commit()
            session.refresh(agent)
        return agent
