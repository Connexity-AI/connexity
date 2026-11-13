"""The single call screen, its recording and `get_call`. Calls are invented."""

import json
import time
import uuid
from collections.abc import Generator
from datetime import timedelta
from typing import Any

import httpx
import pytest
import respx
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core import encryption, security
from app.core.config import settings
from app.core.encryption import encrypt, key_fingerprint, mask_key
from app.models import Agent, Call, User
from app.models.enums import IntegrationProvider, Platform
from app.models.integration import Integration
from app.services.call_screen import MASK, mask_secrets
from app.services.checks.engine import check_call_safely
from app.services.mappings.retell import retell_call_to_trace
from app.tests.utils.retell_payloads import invocation, result, retell_call, speech
from app.tests.utils.utils import extract_cookies, random_email, random_lower_string

API = settings.API_V1_STR
MCP_URL = "https://mcp.example.com/mcp"
ISSUER = "https://backend.example.com"
NOW_MS = int(time.time() * 1000)
CALLER = "+17325554821"
BOOKING = {
    "full_name": "Sam Example",
    "streetAddress": "1 Invented Road",
    "postalCode": "00000",
    "startTime": "2026-10-23T12:00:00-04:00",
    "api_key": "sk-invented-secret",
    "nested": {"token": "tok-invented", "note": "kept"},
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


def _signed_in(client: TestClient, db: Session) -> tuple[User, dict[str, str]]:
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
    return db.exec(select(User).where(User.email == email)).one(), extract_cookies(
        login
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


def _agent(db: Session, user: User, key: str) -> Agent:
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
        name="Front desk",
        platform_agent_name=None,
        created_by=user.id,
    )
    return agent


def _call(
    db: Session,
    agent: Agent,
    *,
    recording: str | None = "https://rec.example.com/old.wav",
) -> Call:
    payload = retell_call(
        f"call_{uuid.uuid4().hex[:10]}",
        agent_id=agent.platform_agent_id or "",
        timeline=[
            speech("agent", "Thank you for calling", 0.5),
            speech("user", "I need a repair", 3.0),
            invocation(
                "t1", "schedule_appointment", json.dumps(BOOKING), time_sec=10.0
            ),
            result(
                "t1",
                '{"status": "booked", "secret": "s3"}',
                successful=True,
                time_sec=10.8,
            ),
            speech("agent", "You are all set", 12.0),
        ],
        start_ms=NOW_MS - 600_000,
        duration_ms=73_000,
        from_number=CALLER,
        recording_url=recording,
        agent_version=88,
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


def test_secrets_are_masked_at_any_depth() -> None:
    masked = mask_secrets(
        {
            "api_key": "x",
            "inner": {"Authorization": "Bearer y", "ok": "z"},
            "list": [{"password": "p"}],
        }
    )

    assert masked == {
        "api_key": MASK,
        "inner": {"Authorization": MASK, "ok": "z"},
        "list": [{"password": MASK}],
    }


def test_the_screen_shows_the_call_and_nothing_more(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    call = _call(db, _agent(db, user, "key_invented_screen"))

    r = client.get(f"{API}/calls/{call.id}/screen", cookies=cookies)

    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["agent_name"], body["caller_last_four"], body["duration_seconds"]) == (
        "Front desk",
        "4821",
        73,
    )
    assert body["version"] == "88"
    assert body["result"] == "failed"
    assert body["has_recording"] is True
    kinds = [(e["kind"], e.get("speaker") or e.get("tool")) for e in body["entries"]]
    assert kinds == [
        ("turn", "agent"),
        ("turn", "caller"),
        ("tool", "schedule_appointment"),
        ("turn", "agent"),
    ]
    tool = body["entries"][2]
    assert (tool["status"], tool["duration_ms"], tool["at_seconds"]) == (
        "ok",
        800,
        10.0,
    )
    arguments = {kv["key"]: kv["value"] for kv in tool["arguments"]}
    assert arguments["api_key"] == MASK
    assert json.loads(arguments["nested"]) == {"token": MASK, "note": "kept"}
    assert arguments["postalCode"] == "00000"
    assert {kv["key"]: kv["value"] for kv in tool["result"]} == {
        "status": "booked",
        "secret": MASK,
    }
    # Never sent: the full number, the platform's payload, the secrets.
    text = json.dumps(body)
    for never in ("7325554821", "sk-invented-secret", "tok-invented", "recording_url"):
        assert never not in text
    (finding,) = body["findings"]
    assert (
        finding["text"]
        == "Booking with missing or placeholder details: schedule_appointment"
    )
    assert (finding["category"], finding["severity"], finding["found_by"]) == (
        "Booking",
        "critical",
        "rule",
    )
    assert finding["entry_index"] == 2
    assert finding["at_seconds"] == 10.0
    assert tool["finding_ids"] == [finding["id"]]


def test_another_workspaces_call_is_not_found(client: TestClient, db: Session) -> None:
    owner, _ = _signed_in(client, db)
    _, cookies = _signed_in(client, db)
    call = _call(db, _agent(db, owner, "key_invented_other"))

    assert (
        client.get(f"{API}/calls/{call.id}/screen", cookies=cookies).status_code == 404
    )
    assert (
        client.get(f"{API}/calls/{call.id}/recording", cookies=cookies).status_code
        == 404
    )


@respx.mock
def test_the_recording_is_asked_of_retell_each_time(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    call = _call(db, _agent(db, user, "key_invented_rec"))
    route = respx.get(f"https://api.retellai.com/v2/get-call/{call.external_id}").mock(
        return_value=httpx.Response(
            200,
            json={
                "call_id": call.external_id,
                "recording_url": "https://rec.example.com/fresh.wav",
            },
        )
    )

    r = client.get(f"{API}/calls/{call.id}/recording", cookies=cookies)

    assert r.json() == {"url": "https://rec.example.com/fresh.wav"}
    assert (
        route.calls.last.request.headers["Authorization"] == "Bearer key_invented_rec"
    )


@respx.mock
@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(500, json={}),
        httpx.Response(200, text="<html>"),
        httpx.TimeoutException("slow"),
    ],
    ids=["error", "not-json", "timeout"],
)
def test_the_stored_recording_is_the_fallback(
    client: TestClient, db: Session, answer: httpx.Response | Exception
) -> None:
    user, cookies = _signed_in(client, db)
    call = _call(db, _agent(db, user, "key_invented_fallback"))
    route = respx.get(f"https://api.retellai.com/v2/get-call/{call.external_id}")
    if isinstance(answer, Exception):
        route.mock(side_effect=answer)
    else:
        route.mock(return_value=answer)

    r = client.get(f"{API}/calls/{call.id}/recording", cookies=cookies)

    assert r.json() == {"url": "https://rec.example.com/old.wav"}


@respx.mock
def test_no_recording_anywhere(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    call = _call(db, _agent(db, user, "key_invented_none"), recording=None)
    respx.get(f"https://api.retellai.com/v2/get-call/{call.external_id}").mock(
        return_value=httpx.Response(200, json={"call_id": call.external_id})
    )

    screen = client.get(f"{API}/calls/{call.id}/screen", cookies=cookies).json()
    recording = client.get(f"{API}/calls/{call.id}/recording", cookies=cookies).json()

    assert screen["has_recording"] is False
    assert recording == {"url": None}


def test_get_call_through_mcp(client: TestClient, db: Session) -> None:
    user, _ = _signed_in(client, db)
    call = _call(db, _agent(db, user, "key_invented_mcp"))

    r = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/calls/{call.id}",
        headers=_headers(user),
    )
    missing = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/calls/{uuid.uuid4()}",
        headers=_headers(user),
    )

    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    assert body["data"]["caller_last_four"] == "4821"
    assert body["data"]["findings"][0]["found_by"] == "rule"
    assert body["guide"] == "connexity://guides/calls"
    assert "7325554821" not in json.dumps(body)
    assert missing.status_code == 404
    assert any("list_calls" in s for s in missing.json()["detail"]["next_steps"])


def test_a_finding_on_two_events_sits_at_the_later_one(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "key_invented_two")
    full = BOOKING | {"postalCode": "07700"}
    payload = retell_call(
        f"call_{uuid.uuid4().hex[:10]}",
        agent_id=agent.platform_agent_id or "",
        timeline=[
            speech("agent", "Hello", 0.5),
            invocation("t1", "schedule_appointment", json.dumps(full), time_sec=30.0),
            result("t1", '{"status": "booked"}', successful=True, time_sec=30.8),
            invocation("t2", "schedule_appointment", json.dumps(full), time_sec=40.0),
            result("t2", '{"status": "booked"}', successful=True, time_sec=40.9),
        ],
        start_ms=NOW_MS - 600_000,
        from_number=CALLER,
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

    body = client.get(f"{API}/calls/{stored.call.id}/screen", cookies=cookies).json()

    (finding,) = body["findings"]
    assert finding["text"] == "Two bookings for one slot: schedule_appointment"
    assert (finding["entry_index"], finding["at_seconds"]) == (2, 40.0)
    # Both bookings show it.
    assert body["entries"][1]["finding_ids"] == [finding["id"]]
    assert body["entries"][2]["finding_ids"] == [finding["id"]]
