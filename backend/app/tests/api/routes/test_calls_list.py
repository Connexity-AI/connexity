"""The Calls page's list and `list_calls`: search, filters, tiles. Calls are invented."""

import json
import time
import uuid
from collections.abc import Generator
from datetime import timedelta
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core import encryption, security
from app.core.config import settings
from app.core.encryption import encrypt, key_fingerprint, mask_key
from app.models import Agent, Call, User, UserCreate
from app.models.enums import IntegrationProvider, Platform
from app.models.integration import Integration
from app.services.checks.engine import check_call_safely
from app.services.mappings.retell import retell_call_to_trace
from app.tests.utils.retell_payloads import invocation, result, retell_call, speech
from app.tests.utils.utils import extract_cookies, random_email, random_lower_string

API = settings.API_V1_STR
MCP_URL = "https://mcp.example.com/mcp"
ISSUER = "https://backend.example.com"
NOW_MS = int(time.time() * 1000)
MINUTE = 60_000
DAY = 86_400_000
FULL = {
    "full_name": "Sam Example",
    "streetAddress": "1 Invented Road",
    "postalCode": "07700",
    "startTime": "2026-10-23T12:00:00-04:00",
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


def _agent(db: Session, company_id: uuid.UUID, user_id: uuid.UUID, name: str) -> Agent:
    key = f"key_invented_{uuid.uuid4().hex[:8]}"
    integration = Integration(
        provider=IntegrationProvider.RETELL,
        name="Retell",
        company_id=company_id,
        encrypted_api_key=encrypt(key),
        masked_api_key=mask_key(key),
        key_fingerprint=key_fingerprint(key),
    )
    db.add(integration)
    db.commit()
    agent, _ = crud.add_platform_agent(
        session=db,
        company_id=company_id,
        integration=integration,
        platform=Platform.RETELL,
        platform_agent_id=f"agent_{uuid.uuid4().hex[:8]}",
        name=name,
        platform_agent_name=None,
        created_by=user_id,
    )
    return agent


def _call(
    db: Session,
    agent: Agent,
    *,
    caller: str,
    minutes_ago: float,
    booking: dict[str, Any] | None = None,
    retell_id: str | None = None,
) -> Call:
    timeline = [speech("agent", "Hello", 0.5)]
    if booking is not None:
        timeline += [
            invocation("t1", "schedule_appointment", json.dumps(booking), time_sec=1.0),
            result("t1", '{"status": "booked"}', successful=True, time_sec=1.5),
        ]
    payload = retell_call(
        retell_id or f"call_{uuid.uuid4().hex[:10]}",
        agent_id=agent.platform_agent_id or "",
        timeline=timeline,
        start_ms=NOW_MS - int(minutes_ago * MINUTE),
        duration_ms=73_000,
        from_number=caller,
    )
    stored = crud.store_trace(
        session=db,
        trace=retell_call_to_trace(payload),
        agent_id=agent.id,
        company_id=agent.company_id,
        integration_id=agent.integration_id,
        raw=payload,
    )
    db.commit()
    check_call_safely(session=db, call=stored.call)
    return stored.call


def _calls(client: TestClient, user: User, **params: str) -> Any:
    r = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/calls",
        headers=_headers(user),
        params=params,
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def workspace(db: Session) -> dict[str, Any]:
    """Four calls: failed (placeholder), clean, unchecked-free; one 40 days old."""
    user = _person(db)
    front = _agent(db, user.company_id, user.id, "Front desk")
    after = _agent(db, user.company_id, user.id, "After hours")
    return {
        "user": user,
        "front": front,
        "after": after,
        "failed": _call(
            db,
            front,
            caller="+17325554821",
            minutes_ago=10,
            booking=FULL | {"postalCode": "00000"},
            retell_id=f"call_retell_{uuid.uuid4().hex[:6]}",
        ),
        "clean": _call(
            db, front, caller="+1 (732) 555-0199", minutes_ago=30, booking=FULL
        ),
        "other": _call(db, after, caller="+442071230000", minutes_ago=60),
        "old": _call(db, front, caller="+17325550123", minutes_ago=40 * 24 * 60),
    }


def test_calls_newest_first_with_the_caller_as_four_digits(
    client: TestClient, workspace: dict[str, Any]
) -> None:
    body = _calls(client, workspace["user"])

    rows = body["data"]["calls"]
    assert [r["id"] for r in rows] == [
        str(workspace["failed"].id),
        str(workspace["clean"].id),
        str(workspace["other"].id),
    ]
    assert [r["caller_last_four"] for r in rows] == ["4821", "0199", "0000"]
    assert rows[0]["agent_name"] == "Front desk"
    assert rows[0]["duration_seconds"] == 73
    assert "7325554821" not in json.dumps(body)
    assert rows[0]["result"] == "failed"
    assert rows[0]["worst_finding"] == {
        "title": "Booking with missing or placeholder details",
        "key": "schedule_appointment",
        "category": "Booking",
        "severity": "critical",
        "found_by": "rule",
    }
    assert rows[1]["result"] == "clean"
    assert rows[1]["worst_finding"] is None
    assert body["data"]["tiles"] == {
        "calls": 3,
        "failed": 1,
        "degraded": 0,
        "clean": 2,
        "unchecked": 0,
    }


def test_the_period_decides_which_calls_count(
    client: TestClient, workspace: dict[str, Any]
) -> None:
    assert _calls(client, workspace["user"], period="7d")["data"]["tiles"]["calls"] == 3
    longer = _calls(client, workspace["user"], period="90d")["data"]
    assert longer["tiles"]["calls"] == 4
    assert longer["calls"][-1]["id"] == str(workspace["old"].id)


def test_filters_narrow_the_list_and_the_result_leaves_the_tiles(
    client: TestClient, workspace: dict[str, Any]
) -> None:
    user = workspace["user"]

    failed = _calls(client, user, result="failed")["data"]
    assert [r["id"] for r in failed["calls"]] == [str(workspace["failed"].id)]
    assert failed["tiles"]["calls"] == 3

    agent = _calls(client, user, agent_id=str(workspace["after"].id))["data"]
    assert [r["id"] for r in agent["calls"]] == [str(workspace["other"].id)]
    assert agent["tiles"]["calls"] == 1

    booking = _calls(client, user, category="booking")["data"]
    assert [r["id"] for r in booking["calls"]] == [str(workspace["failed"].id)]


@pytest.mark.parametrize(
    "query",
    ["4821", "+1 732 555 4821", "(732) 555-4821", "17325554821"],
)
def test_search_by_phone_number(
    client: TestClient, workspace: dict[str, Any], query: str
) -> None:
    rows = _calls(client, workspace["user"], query=query)["data"]["calls"]

    assert [r["id"] for r in rows] == [str(workspace["failed"].id)]


def test_search_by_call_id(client: TestClient, workspace: dict[str, Any]) -> None:
    user, call = workspace["user"], workspace["failed"]

    by_ours = _calls(client, user, query=str(call.id))["data"]["calls"]
    by_retell = _calls(client, user, query=call.external_id)["data"]["calls"]

    assert [r["id"] for r in by_ours] == [str(call.id)]
    assert [r["id"] for r in by_retell] == [str(call.id)]


def test_no_match_says_how_search_works(
    client: TestClient, workspace: dict[str, Any]
) -> None:
    body = _calls(client, workspace["user"], query="call_nothing_like_it")

    assert body["data"]["calls"] == []
    assert any("end of the caller's number" in s for s in body["next_steps"])


def test_paging(client: TestClient, workspace: dict[str, Any]) -> None:
    user = workspace["user"]

    first = _calls(client, user, limit="2")
    second = _calls(client, user, limit="2", cursor=first["next_cursor"])

    assert len(first["data"]["calls"]) == 2
    assert [r["id"] for r in second["data"]["calls"]] == [str(workspace["other"].id)]
    assert second["next_cursor"] is None


def test_another_workspace_is_not_found(client: TestClient, db: Session) -> None:
    user, other = _person(db), _person(db)

    r = client.get(
        f"{API}/mcp/workspaces/{other.company_id}/calls", headers=_headers(user)
    )

    assert r.status_code == 404


def test_the_web_page_lists_the_open_workspaces_calls(
    client: TestClient, db: Session
) -> None:
    email, password = random_email(), random_lower_string()
    assert (
        client.post(
            f"{API}/users/signup", json={"email": email, "password": password}
        ).status_code
        == 200
    )
    login = client.post(
        f"{API}/login/access-token", data={"username": email, "password": password}
    )
    cookies = extract_cookies(login)
    user = db.exec(select(User).where(User.email == email)).one()
    agent = _agent(db, user.company_id, user.id, "Front desk")
    call = _call(db, agent, caller="+17325554821", minutes_ago=5)

    r = client.get(f"{API}/calls", cookies=cookies, params={"q": "4821"})

    assert r.status_code == 200, r.text
    body = r.json()
    assert [row["id"] for row in body["data"]] == [str(call.id)]
    assert body["data"][0]["caller_last_four"] == "4821"
    assert body["tiles"]["calls"] == 1
    assert body["period"] == "30d"
    assert [a["label"] for a in body["agents"]] == ["Front desk"]
    assert [c["value"] for c in body["categories"]][:3] == [
        "greeting_and_identification",
        "information_collection",
        "booking",
    ]
    assert body["has_more"] is False
