"""Personal access tokens: created on the web, used by an assistant over MCP."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.models import User, UserCreate
from app.models.personal_access_token import PersonalAccessToken
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


def _create(client: TestClient, user: User) -> dict:
    r = client.post(f"{API}/personal-access-tokens", cookies=_web(user))
    assert r.status_code == 201, r.text
    return r.json()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _workspaces(client: TestClient, token: str):
    return client.get(f"{API}/mcp/workspaces", headers=_bearer(token))


def _listed(client: TestClient, user: User) -> list[dict]:
    r = client.get(f"{API}/personal-access-tokens", cookies=_web(user))
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _assistant_step(client: TestClient, user: User) -> tuple[str, str]:
    body = client.get(f"{API}/readiness", cookies=_web(user)).json()
    step = body["steps"][0]
    return step["state"], step["detail"]


# ── Creating, listing, revoking on the web ──


def test_creating_answers_the_token_once_inside_the_setup_prompt(
    client: TestClient, db: Session
) -> None:
    user = _person(db)

    body = _create(client, user)

    token = body["token"]
    assert token.startswith("cxp_")
    assert len(token) > 40
    assert body["name"] == "Claude Code"
    assert token.startswith(body["prefix"])
    assert body["last_used_at"] is None
    prompt = body["setup_prompt"]
    assert (
        f"claude mcp add --transport http --scope user connexity {MCP_URL} "
        f'--header "Authorization: Bearer {token}"'
    ) in prompt
    assert "do not repeat the token" in prompt

    listed = _listed(client, user)
    assert [t["id"] for t in listed] == [body["id"]]
    assert "token" not in listed[0]
    assert token not in str(listed)

    stored = db.get(PersonalAccessToken, uuid.UUID(body["id"]))
    assert stored is not None
    assert token not in (stored.token_hash, stored.prefix)


def test_creating_again_revokes_the_unused_one_but_not_a_used_one(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    used = _create(client, user)
    assert _workspaces(client, used["token"]).status_code == 200
    unused = _create(client, user)

    latest = _create(client, user)

    assert {t["id"] for t in _listed(client, user)} == {used["id"], latest["id"]}
    assert _workspaces(client, unused["token"]).status_code == 401
    assert _workspaces(client, used["token"]).status_code == 200


def test_tokens_need_a_signed_in_person(client: TestClient) -> None:
    assert client.post(f"{API}/personal-access-tokens").status_code == 401
    assert client.get(f"{API}/personal-access-tokens").status_code == 401


def test_without_an_mcp_address_no_token_is_created(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", None)
    monkeypatch.setattr(settings, "MCP_OAUTH_AUDIENCE", None)
    user = _person(db)

    r = client.post(f"{API}/personal-access-tokens", cookies=_web(user))

    assert r.status_code == 409
    assert crud.list_personal_access_tokens(session=db, user_id=user.id) == []


def test_revoking_cuts_the_assistant_off(client: TestClient, db: Session) -> None:
    user = _person(db)
    created = _create(client, user)
    assert _workspaces(client, created["token"]).status_code == 200

    r = client.delete(
        f"{API}/personal-access-tokens/{created['id']}", cookies=_web(user)
    )

    assert r.status_code == 204
    assert _workspaces(client, created["token"]).status_code == 401
    assert _listed(client, user) == []
    again = client.delete(
        f"{API}/personal-access-tokens/{created['id']}", cookies=_web(user)
    )
    assert again.status_code == 404


def test_another_persons_token_cannot_be_revoked(
    client: TestClient, db: Session
) -> None:
    owner = _person(db)
    other = _person(db)
    created = _create(client, owner)

    r = client.delete(
        f"{API}/personal-access-tokens/{created['id']}", cookies=_web(other)
    )

    assert r.status_code == 404
    assert _workspaces(client, created["token"]).status_code == 200
    assert _listed(client, other) == []


# ── Using a token over MCP ──


def test_a_token_reaches_exactly_the_persons_workspaces(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    other = _person(db)
    token = _create(client, user)["token"]

    r = _workspaces(client, token)

    assert r.status_code == 200, r.text
    assert [w["id"] for w in r.json()["data"]] == [str(user.company_id)]
    elsewhere = client.get(
        f"{API}/mcp/workspaces/{other.company_id}/readiness", headers=_bearer(token)
    )
    assert elsewhere.status_code == 404


def test_using_a_token_records_when(client: TestClient, db: Session) -> None:
    user = _person(db)
    created = _create(client, user)

    _workspaces(client, created["token"])

    [listed] = _listed(client, user)
    assert listed["last_used_at"] is not None


@pytest.mark.parametrize(
    "token",
    ["cxp_" + "x" * 43, "cxp_", "not-a-token"],
    ids=["made-up", "prefix-only", "garbage"],
)
def test_an_unknown_token_is_refused(client: TestClient, token: str) -> None:
    assert _workspaces(client, token).status_code == 401


def test_a_deactivated_persons_token_is_refused(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    token = _create(client, user)["token"]
    user.is_active = False
    db.add(user)
    db.commit()

    assert _workspaces(client, token).status_code == 401


def test_the_web_session_token_is_not_an_mcp_token(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    session_token = _web(user)[settings.AUTH_COOKIE]

    assert _workspaces(client, session_token).status_code == 401


def test_last_used_is_written_at_most_once_a_minute(db: Session) -> None:
    user = _person(db)
    row, token = crud.create_personal_access_token(
        session=db, user_id=user.id, name="Claude Code"
    )
    crud.use_personal_access_token(session=db, token=token)
    first = row.last_used_at
    assert first is not None

    crud.use_personal_access_token(session=db, token=token)
    assert row.last_used_at == first

    row.last_used_at = datetime.now(UTC) - timedelta(minutes=2)
    db.add(row)
    db.commit()
    crud.use_personal_access_token(session=db, token=token)
    assert row.last_used_at is not None
    assert row.last_used_at > first


# ── Readiness step 1 ──


def test_step_one_ticks_on_the_first_use_and_unticks_on_revoke(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    created = _create(client, user)
    assert _assistant_step(client, user)[0] == "not_started"

    _workspaces(client, created["token"])

    assert _assistant_step(client, user) == ("done", "Claude Code")
    client.delete(f"{API}/personal-access-tokens/{created['id']}", cookies=_web(user))
    assert _assistant_step(client, user)[0] == "not_started"


def test_a_token_ticks_step_one_in_every_workspace_of_the_person_only(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    other = _person(db)
    token = _create(client, user)["token"]
    second = client.post(
        f"{API}/mcp/workspaces", headers=_bearer(token), json={"name": "Second"}
    )
    assert second.status_code in (200, 201), second.text
    second_id = second.json()["data"]["id"]

    readiness = client.get(
        f"{API}/mcp/workspaces/{second_id}/readiness", headers=_bearer(token)
    )

    assert readiness.json()["data"]["steps"][0]["state"] == "done"
    assert _assistant_step(client, user)[0] == "done"
    assert _assistant_step(client, other)[0] == "not_started"
