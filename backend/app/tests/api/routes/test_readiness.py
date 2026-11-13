import secrets
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.models import User, UserCreate
from app.models.enums import IntegrationProvider
from app.models.integration import Integration
from app.models.oauth import OAuthClient, OAuthRefreshToken
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
MCP_URL = "https://mcp.example.com/mcp"
ISSUER = "https://backend.example.com"


@pytest.fixture(autouse=True)
def _mcp_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)


def _person(db: Session) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )


def _web(user: User) -> dict[str, str]:
    token, _ = security.create_session_token(
        user_id=user.id, company_id=user.company_id
    )
    return {settings.AUTH_COOKIE: token}


def _connect_assistant(
    db: Session,
    user: User,
    *,
    name: str = "Claude Code",
    expires_in: timedelta = timedelta(days=30),
    revoked: bool = False,
) -> None:
    client = OAuthClient(
        client_id=f"client-{uuid.uuid4().hex}",
        client_name=name,
        redirect_uris=["https://claude.ai/api/mcp/auth_callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
    )
    db.add(client)
    db.flush()
    db.add(
        OAuthRefreshToken(
            token_hash=secrets.token_hex(32),
            company_id=user.company_id,
            client_id=client.client_id,
            user_id=user.id,
            resource=MCP_URL,
            expires_at=datetime.now(UTC) + expires_in,
            revoked_at=datetime.now(UTC) if revoked else None,
        )
    )
    db.commit()


def _connect_platform(
    db: Session, company_id: uuid.UUID, provider: IntegrationProvider
) -> None:
    db.add(
        Integration(
            provider=provider,
            name="Production",
            company_id=company_id,
            encrypted_api_key="encrypted",
            masked_api_key="key_****",
        )
    )
    db.commit()


def _steps(client: TestClient, user: User) -> dict[str, tuple[str, str | None]]:
    r = client.get(f"{API}/readiness", cookies=_web(user))
    assert r.status_code == 200, r.text
    return {s["key"]: (s["state"], s["detail"]) for s in r.json()["steps"]}


def test_a_new_workspace_has_nothing_done_and_gives_the_mcp_address(
    client: TestClient, db: Session
) -> None:
    user = _person(db)

    body = client.get(f"{API}/readiness", cookies=_web(user)).json()

    assert [(s["key"], s["state"]) for s in body["steps"]] == [
        ("assistant", "not_started"),
        ("voice_platform", "not_started"),
        ("sync", "not_started"),
        ("first_scan", "not_started"),
    ]
    assert (body["done"], body["total"], body["percent"]) == (0, 4, 0)
    assert body["first_scan_done"] is False
    assert body["mcp_url"] == MCP_URL


def test_a_connected_assistant_ticks_step_one(client: TestClient, db: Session) -> None:
    user = _person(db)
    _connect_assistant(db, user, name="Claude Code")

    body = client.get(f"{API}/readiness", cookies=_web(user)).json()

    assert body["steps"][0] == {
        "key": "assistant",
        "name": "Assistant connected",
        "state": "done",
        "detail": "Claude Code",
    }
    assert (body["done"], body["percent"]) == (1, 25)


@pytest.mark.parametrize(
    "grant",
    [{"revoked": True}, {"expires_in": timedelta(seconds=-1)}],
    ids=["revoked", "expired"],
)
def test_a_revoked_or_expired_connection_does_not_count(
    client: TestClient, db: Session, grant: dict[str, object]
) -> None:
    user = _person(db)
    _connect_assistant(db, user, **grant)  # type: ignore[arg-type]

    assert _steps(client, user)["assistant"][0] == "not_started"


def test_a_voice_platform_ticks_step_two_but_n8n_does_not(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    _connect_platform(db, user.company_id, IntegrationProvider.N8N)
    assert _steps(client, user)["voice_platform"] == ("not_started", None)

    _connect_platform(db, user.company_id, IntegrationProvider.RETELL)

    assert _steps(client, user)["voice_platform"] == ("done", "Retell")


def test_another_workspace_does_not_count(client: TestClient, db: Session) -> None:
    user = _person(db)
    other = _person(db)
    _connect_assistant(db, other)
    _connect_platform(db, other.company_id, IntegrationProvider.RETELL)

    steps = _steps(client, user)

    assert steps["assistant"][0] == "not_started"
    assert steps["voice_platform"][0] == "not_started"


def test_without_an_mcp_address_there_is_none(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", None)
    monkeypatch.setattr(settings, "MCP_OAUTH_AUDIENCE", None)
    user = _person(db)

    body = client.get(f"{API}/readiness", cookies=_web(user)).json()

    assert body["mcp_url"] is None


def _mcp(user: User) -> dict[str, str]:
    token, _ = security.create_oauth_access_token(
        subject=user.id,
        audience=MCP_URL,
        issuer=ISSUER,
        client_id="claude-client",
        scope="mcp:access",
        expires_delta=timedelta(minutes=60),
    )
    return {"Authorization": f"Bearer {token}"}


def test_mcp_get_readiness_answers_in_the_standard_shape(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    _connect_assistant(db, user)

    r = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/readiness", headers=_mcp(user)
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["guide"] == "connexity://guides/readiness"
    assert body["rules"]
    assert body["data"]["steps"][0]["state"] == "done"
    assert any("Retell" in step for step in body["next_steps"])
    assert any("get_readiness" in step for step in body["next_steps"])


def test_mcp_get_readiness_in_another_workspace_is_not_found(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    other = _person(db)

    r = client.get(
        f"{API}/mcp/workspaces/{other.company_id}/readiness", headers=_mcp(user)
    )

    assert r.status_code == 404


def test_a_connection_without_a_refresh_token_counts_while_its_access_token_lasts(
    client: TestClient, db: Session
) -> None:
    from app.models.oauth import OAuthAuthorizationCode

    user = _person(db)
    oauth_client = OAuthClient(
        client_id=f"client-{uuid.uuid4().hex}",
        client_name="ChatGPT",
        redirect_uris=["https://claude.ai/api/mcp/auth_callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
    )
    db.add(oauth_client)
    db.flush()

    def exchange(minutes_ago: int) -> None:
        now = datetime.now(UTC)
        db.add(
            OAuthAuthorizationCode(
                code=secrets.token_hex(16),
                company_id=user.company_id,
                client_id=oauth_client.client_id,
                user_id=user.id,
                redirect_uri="https://claude.ai/api/mcp/auth_callback",
                resource=MCP_URL,
                code_challenge="challenge",
                expires_at=now,
                consumed_at=now - timedelta(minutes=minutes_ago),
            )
        )
        db.commit()

    exchange(settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES + 5)
    assert _steps(client, user)["assistant"][0] == "not_started"

    exchange(5)
    assert _steps(client, user)["assistant"] == ("done", "ChatGPT")


def test_mcp_next_steps_do_not_ask_for_a_platform_already_connected(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    _connect_platform(db, user.company_id, IntegrationProvider.RETELL)

    body = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/readiness", headers=_mcp(user)
    ).json()

    assert not any("ask the person for their Retell" in s for s in body["next_steps"])
    assert any("do not ask for the key again" in s for s in body["next_steps"])
