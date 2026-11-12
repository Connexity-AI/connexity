import uuid
from collections.abc import Generator
from datetime import timedelta

import httpx
import pytest
import respx
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core import encryption, security
from app.core.config import settings
from app.core.encryption import encrypt, mask_key
from app.models import Agent, User, UserCreate
from app.models.enums import IntegrationProvider
from app.models.integration import Integration
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
MCP_URL = "https://mcp.example.com/mcp"
ISSUER = "https://backend.example.com"
RETELL_LIST_AGENTS = "https://api.retellai.com/v2/list-agents"

ACCOUNT = {
    "items": [
        {
            "agent_id": "agent_front",
            "agent_name": "Front desk",
            "latest_published_version": 3,
        },
        # Retell lists an agent once per version.
        {"agent_id": "agent_front", "agent_name": "Front desk (draft)"},
        {"agent_id": "agent_after", "agent_name": "After hours"},
        {"agent_id": "agent_other", "agent_name": "Another client's agent"},
    ],
    "has_more": False,
}


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    yield
    encryption._fernet.cache_clear()


def _person(db: Session) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )


def _headers(user: User) -> dict[str, str]:
    token, _ = security.create_oauth_access_token(
        subject=user.id,
        audience=MCP_URL,
        issuer=ISSUER,
        client_id="claude-code",
        scope="mcp:access",
        expires_delta=timedelta(minutes=60),
    )
    return {"Authorization": f"Bearer {token}"}


def _connect_retell(db: Session, company_id: uuid.UUID) -> Integration:
    integration = Integration(
        provider=IntegrationProvider.RETELL,
        name="Retell",
        company_id=company_id,
        encrypted_api_key=encrypt("key_test"),
        masked_api_key=mask_key("key_test"),
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def _add(
    client: TestClient,
    user: User,
    agents: list[dict[str, str]],
    workspace: uuid.UUID | None = None,
) -> httpx.Response:
    return client.post(
        f"{API}/mcp/workspaces/{workspace or user.company_id}/agents",
        headers=_headers(user),
        json={"agents": agents},
    )


@respx.mock
def test_adding_agents_links_them_to_the_retell_connection(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    integration = _connect_retell(db, user.company_id)
    respx.post(RETELL_LIST_AGENTS).mock(return_value=httpx.Response(200, json=ACCOUNT))

    r = _add(
        client,
        user,
        [
            {"platform_agent_id": "agent_front"},
            {"platform_agent_id": "agent_after", "name": "Clinic after-hours"},
        ],
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert [
        (a["name"], a["platform_agent_id"], a["platform_agent_name"])
        for a in body["data"]["added"]
    ] == [
        ("Front desk", "agent_front", "Front desk"),
        ("Clinic after-hours", "agent_after", "After hours"),
    ]
    assert body["data"]["already_added"] == []
    assert body["data"]["refused"] == []
    agents = db.exec(select(Agent).where(Agent.company_id == user.company_id)).all()
    assert {a.platform_agent_id for a in agents} == {"agent_front", "agent_after"}
    for agent in agents:
        assert agent.integration_id == integration.id
        assert agent.platform == "retell"
        assert agent.created_by == user.id

    listed = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents", headers=_headers(user)
    ).json()["data"]
    assert {a["platform_agent_id"] for a in listed} == {"agent_front", "agent_after"}

    readiness = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/readiness", headers=_headers(user)
    ).json()["data"]["steps"][2]
    assert (readiness["state"], readiness["detail"]) == (
        "in_progress",
        "2 agents · 0 calls",
    )

    address = f"{ISSUER}{API}/webhooks/retell/{integration.id}"
    assert any(address in step for step in body["next_steps"])
    readiness_steps = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/readiness", headers=_headers(user)
    ).json()["next_steps"]
    waiting = next(s for s in readiness_steps if "No call has arrived by webhook" in s)
    assert "Front desk" in waiting
    assert "Clinic after-hours" in waiting
    assert address in waiting


@respx.mock
def test_already_added_and_unknown_ids(client: TestClient, db: Session) -> None:
    user = _person(db)
    _connect_retell(db, user.company_id)
    respx.post(RETELL_LIST_AGENTS).mock(return_value=httpx.Response(200, json=ACCOUNT))
    _add(client, user, [{"platform_agent_id": "agent_front"}])

    r = _add(
        client,
        user,
        [
            {"platform_agent_id": "agent_front"},
            {"platform_agent_id": "agent_typo"},
            {"platform_agent_id": "agent_typo"},
        ],
    )

    body = r.json()["data"]
    assert body["added"] == []
    assert [a["platform_agent_id"] for a in body["already_added"]] == ["agent_front"]
    assert body["refused"] == [
        {
            "platform_agent_id": "agent_typo",
            "reason": "Not an agent in the connected Retell account",
        }
    ]
    assert any("refused" in s for s in r.json()["next_steps"])
    count = len(db.exec(select(Agent).where(Agent.company_id == user.company_id)).all())
    assert count == 1


def test_without_a_retell_connection(client: TestClient, db: Session) -> None:
    user = _person(db)

    r = _add(client, user, [{"platform_agent_id": "agent_front"}])

    assert r.status_code == 409
    assert any("connect_voice_platform" in s for s in r.json()["detail"]["next_steps"])


@respx.mock
@pytest.mark.parametrize(
    "retell",
    [
        httpx.Response(500, text="error"),
        httpx.Response(200, json={"unexpected": True}),
        httpx.Response(200, text="not json"),
        httpx.TimeoutException("timed out"),
    ],
    ids=["error", "malformed", "not-json", "timeout"],
)
def test_retell_unreachable_adds_nothing(
    client: TestClient, db: Session, retell: httpx.Response | Exception
) -> None:
    user = _person(db)
    _connect_retell(db, user.company_id)
    route = respx.post(RETELL_LIST_AGENTS)
    if isinstance(retell, Exception):
        route.mock(side_effect=retell)
    else:
        route.mock(return_value=retell)

    r = _add(client, user, [{"platform_agent_id": "agent_front"}])

    assert r.status_code == 503
    assert r.json()["detail"]["error"] == (
        "Retell could not be reached to check the agent ids"
    )
    assert db.exec(select(Agent).where(Agent.company_id == user.company_id)).all() == []


def test_another_workspace_is_not_found(client: TestClient, db: Session) -> None:
    user = _person(db)
    other = _person(db)
    _connect_retell(db, other.company_id)

    r = _add(client, user, [{"platform_agent_id": "agent_front"}], other.company_id)

    assert r.status_code == 404


def test_the_request_is_validated(client: TestClient, db: Session) -> None:
    user = _person(db)

    assert _add(client, user, []).status_code == 422
    assert _add(client, user, [{"platform_agent_id": "  "}]).status_code == 422
    too_many = [{"platform_agent_id": f"agent_{i}"} for i in range(101)]
    assert _add(client, user, too_many).status_code == 422


@respx.mock
def test_a_revoked_stored_key_asks_to_reconnect(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    _connect_retell(db, user.company_id)
    respx.post(RETELL_LIST_AGENTS).mock(return_value=httpx.Response(401, json={}))

    r = _add(client, user, [{"platform_agent_id": "agent_front"}])

    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["error"] == "Retell refused the key stored for this workspace"
    assert any("connect_voice_platform" in s for s in detail["next_steps"])
