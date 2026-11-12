import secrets
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
from app.core.encryption import decrypt
from app.models import User, UserCreate
from app.models.integration import Integration
from app.models.oauth import OAuthClient
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
MCP_URL = "https://mcp.example.com/mcp"
ISSUER = "https://backend.example.com"
RETELL_LIST_AGENTS = "https://api.retellai.com/v2/list-agents"
KEY = "key_" + "a1b2c3d4e5f6g7h8i9j0"


@pytest.fixture(autouse=True)
def _mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """A real Fernet key: CI's ENCRYPTION_KEY is a placeholder."""
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    yield
    encryption._fernet.cache_clear()


def _person(db: Session) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=random_lower_string(), full_name="Ann"
        ),
    )


def _assistant_token(
    db: Session, user: User, name: str = "Claude Code"
) -> dict[str, str]:
    client = OAuthClient(
        client_id=f"client-{uuid.uuid4().hex}",
        client_name=name,
        redirect_uris=["http://localhost/callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
    )
    db.add(client)
    db.commit()
    token, _ = security.create_oauth_access_token(
        subject=user.id,
        audience=MCP_URL,
        issuer=ISSUER,
        client_id=client.client_id,
        scope="mcp:access",
        expires_delta=timedelta(minutes=60),
    )
    return {"Authorization": f"Bearer {token}"}


def _connect(
    client: TestClient, headers: dict[str, str], workspace_id: uuid.UUID, key: str = KEY
) -> httpx.Response:
    return client.post(
        f"{API}/mcp/workspaces/{workspace_id}/connections",
        headers=headers,
        json={"platform": "retell", "api_key": key},
    )


def _integrations(db: Session, company_id: uuid.UUID) -> list[Integration]:
    db.expire_all()
    return list(
        db.exec(select(Integration).where(Integration.company_id == company_id)).all()
    )


@respx.mock
def test_connecting_retell_stores_the_key_and_ticks_readiness(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    headers = _assistant_token(db, user)
    route = respx.post(RETELL_LIST_AGENTS).mock(
        return_value=httpx.Response(200, json=[])
    )

    r = _connect(client, headers, user.company_id)

    assert r.status_code == 200, r.text
    assert route.call_count == 1
    assert route.calls.last.request.headers["Authorization"] == f"Bearer {KEY}"
    body = r.json()
    assert body["data"]["platform"] == "Retell"
    assert body["data"]["replaced_earlier_key"] is False
    assert body["data"]["connected_by"] == "Ann through Claude Code"
    assert KEY not in r.text
    assert body["guide"] == "connexity://guides/connect"
    [integration] = _integrations(db, user.company_id)
    assert decrypt(integration.encrypted_api_key) == KEY
    assert integration.created_by_user_id == user.id
    assert integration.created_via == "Claude Code"

    readiness = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/readiness", headers=headers
    ).json()
    assert readiness["data"]["steps"][1] == {
        "key": "voice_platform",
        "name": "Voice platform connected",
        "state": "done",
        "detail": "Retell",
    }


@respx.mock
def test_connecting_again_replaces_the_key(client: TestClient, db: Session) -> None:
    user = _person(db)
    respx.post(RETELL_LIST_AGENTS).mock(return_value=httpx.Response(200, json=[]))
    _connect(client, _assistant_token(db, user, "Claude Code"), user.company_id)
    new_key = "key_" + secrets.token_hex(10)

    r = _connect(
        client, _assistant_token(db, user, "ChatGPT"), user.company_id, new_key
    )

    assert r.status_code == 200, r.text
    assert r.json()["data"]["replaced_earlier_key"] is True
    assert any("replaced" in step for step in r.json()["next_steps"])
    [integration] = _integrations(db, user.company_id)
    assert decrypt(integration.encrypted_api_key) == new_key
    assert integration.created_via == "ChatGPT"


@respx.mock
def test_a_key_retell_refuses_is_refused(client: TestClient, db: Session) -> None:
    user = _person(db)
    respx.post(RETELL_LIST_AGENTS).mock(
        return_value=httpx.Response(401, json={"error": "invalid api key"})
    )

    r = _connect(client, _assistant_token(db, user), user.company_id)

    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["error"] == "Retell refused this API key"
    assert any("API Keys" in step for step in detail["next_steps"])
    assert KEY not in r.text
    assert _integrations(db, user.company_id) == []


@respx.mock
@pytest.mark.parametrize(
    "retell",
    [
        httpx.Response(500, text="server error"),
        httpx.Response(200, text=""),
        httpx.TimeoutException("timed out"),
        httpx.ConnectError("unreachable"),
    ],
    ids=["server-error", "empty-but-ok", "timeout", "unreachable"],
)
def test_retell_failing_is_not_called_a_refused_key(
    client: TestClient, db: Session, retell: httpx.Response | Exception
) -> None:
    user = _person(db)
    route = respx.post(RETELL_LIST_AGENTS)
    if isinstance(retell, Exception):
        route.mock(side_effect=retell)
    else:
        route.mock(return_value=retell)

    r = _connect(client, _assistant_token(db, user), user.company_id)

    if isinstance(retell, httpx.Response) and retell.status_code == 200:
        # An empty 200 still means Retell accepted the key.
        assert r.status_code == 200, r.text
        return
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert detail["error"] == "Retell could not be reached to check the key"
    assert any("again in a minute" in step for step in detail["next_steps"])
    assert _integrations(db, user.company_id) == []


def test_another_workspace_is_not_found(client: TestClient, db: Session) -> None:
    user = _person(db)
    other = _person(db)

    with respx.mock(assert_all_called=False) as retell:
        route = retell.post(RETELL_LIST_AGENTS)
        r = _connect(client, _assistant_token(db, user), other.company_id)

    assert r.status_code == 404
    assert not route.called


def test_an_unknown_platform_or_blank_key_is_invalid(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    headers = _assistant_token(db, user)
    url = f"{API}/mcp/workspaces/{user.company_id}/connections"

    assert (
        client.post(
            url, headers=headers, json={"platform": "n8n", "api_key": KEY}
        ).status_code
        == 422
    )
    assert (
        client.post(
            url, headers=headers, json={"platform": "retell", "api_key": ""}
        ).status_code
        == 422
    )
