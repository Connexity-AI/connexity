"""`list_issues` through MCP, on invented calls checked by the real engine."""

import json
import time
import uuid
from collections.abc import Generator
from datetime import timedelta
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core import encryption, security
from app.core.config import settings
from app.core.encryption import encrypt, key_fingerprint, mask_key
from app.models import Agent, User, UserCreate
from app.models.enums import IntegrationProvider, Platform
from app.models.integration import Integration
from app.services.checks.engine import check_call_safely
from app.services.mappings.retell import retell_call_to_trace
from app.tests.utils.retell_payloads import invocation, result, retell_call, speech
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
MCP_URL = "https://mcp.example.com/mcp"
ISSUER = "https://backend.example.com"
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


def _agent(db: Session, user: User, name: str) -> Agent:
    key = f"key_invented_{uuid.uuid4().hex[:8]}"
    integration = Integration(
        provider=IntegrationProvider.RETELL,
        name="Retell",
        company_id=user.company_id,
        encrypted_api_key=encrypt(key),
        masked_api_key=mask_key(key),
        key_fingerprint=key_fingerprint(key),
    )
    db.add(integration)
    db.commit()
    agent, _ = crud.add_platform_agent(
        session=db,
        company_id=user.company_id,
        integration=integration,
        platform=Platform.RETELL,
        platform_agent_id=f"agent_{uuid.uuid4().hex[:8]}",
        name=name,
        platform_agent_name=None,
        created_by=user.id,
    )
    return agent


def _booking(n: int, args: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        invocation(f"t{n}", "schedule_appointment", json.dumps(args), time_sec=1.0 + n),
        result(f"t{n}", '{"status": "booked"}', successful=True, time_sec=1.5 + n),
    ]


DAY_MS = 86_400_000


def _call(
    db: Session, agent: Agent, *bookings: list[dict[str, Any]], days_ago: float = 1
) -> uuid.UUID:
    payload = retell_call(
        f"call_{uuid.uuid4().hex[:8]}",
        agent_id=agent.platform_agent_id or "",
        timeline=[speech("agent", "Hello", 0.5)] + [e for b in bookings for e in b],
        start_ms=int(time.time() * 1000 - days_ago * DAY_MS),
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
    return stored.call.id


def _issues(client: TestClient, user: User, **params: str) -> Any:
    return client.get(
        f"{API}/mcp/workspaces/{user.company_id}/issues",
        headers=_headers(user),
        params=params,
    )


def test_issues_come_worst_first_with_how_they_were_found(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Front desk")
    # Placeholder details on two calls, then booked again at the same time on one.
    _call(db, agent, _booking(1, FULL | {"streetAddress": ""}), _booking(2, FULL))
    _call(db, agent, _booking(1, FULL | {"full_name": "{{full_name}}"}))
    _call(db, agent, _booking(1, FULL))

    r = _issues(client, user)

    assert r.status_code == 200, r.text
    body = r.json()
    issues = body["data"]["issues"]
    rows = [
        (
            i["check_type"],
            i["severity"],
            i["found_by"],
            i["category"],
            i["calls_affected"],
            i["calls_total"],
        )
        for i in issues
    ]
    assert rows == [
        ("booking_details_missing", "critical", "rule", "booking", 2, 3),
        ("booking_duplicated", "critical", "rule", "booking", 1, 3),
    ]
    assert issues[0]["agent_name"] == "Front desk"
    assert issues[0]["title"] == (
        "Booking with missing or placeholder details: schedule_appointment"
    )
    assert body["data"]["tiles"] == {
        "open": 2,
        "critical": 2,
        "reopened": 0,
        "resolved": 0,
        "calls_affected": 2,
        "calls": 3,
    }
    assert body["guide"] == "connexity://guides/issues"
    assert any("found_by" in rule for rule in body["rules"])


def test_issues_of_one_agent_and_paging(client: TestClient, db: Session) -> None:
    user = _person(db)
    first = _agent(db, user, "First")
    second = _agent(db, user, "Second")
    _call(db, first, _booking(1, FULL | {"postalCode": "00000"}))
    _call(db, second, _booking(1, FULL), _booking(2, FULL))

    only = _issues(client, user, agent_id=str(second.id)).json()["data"]
    assert [i["check_type"] for i in only["issues"]] == ["booking_duplicated"]
    assert only["tiles"]["calls"] == 1

    page = _issues(client, user, limit="1").json()
    assert len(page["data"]["issues"]) == 1
    assert page["next_cursor"]
    rest = _issues(client, user, limit="1", cursor=page["next_cursor"]).json()
    assert len(rest["data"]["issues"]) == 1
    assert rest["data"]["issues"][0]["id"] != page["data"]["issues"][0]["id"]
    assert rest["next_cursor"] is None


def test_no_issues_says_what_to_do(client: TestClient, db: Session) -> None:
    user = _person(db)

    body = _issues(client, user).json()

    assert body["data"]["issues"] == []
    assert any("get_readiness" in s for s in body["next_steps"])


def test_the_search_and_filters_narrow_the_issues(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Front desk")
    _call(db, agent, _booking(1, FULL | {"streetAddress": ""}), _booking(2, FULL))

    def types(**params: str) -> list[str]:
        r = _issues(client, user, **params)
        assert r.status_code == 200, r.text
        return [i["check_type"] for i in r.json()["data"]["issues"]]

    assert types(query="two bookings") == ["booking_duplicated"]
    assert types(severity="warning") == []
    # One call each, so their order is by when they were last seen.
    assert sorted(types(category="booking", severity="critical")) == [
        "booking_details_missing",
        "booking_duplicated",
    ]
    assert types(status="archived") == []
    nothing = _issues(client, user, query="nothing like this").json()
    assert any("No issue matches" in s for s in nothing["next_steps"])
    assert _issues(client, user, status="regressed").status_code == 422


def test_another_workspace_or_agent_is_not_found(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    other = _person(db)
    elsewhere = _agent(db, other, "Elsewhere")

    assert (
        client.get(
            f"{API}/mcp/workspaces/{other.company_id}/issues", headers=_headers(user)
        ).status_code
        == 404
    )
    assert _issues(client, user, agent_id=str(elsewhere.id)).status_code == 404
