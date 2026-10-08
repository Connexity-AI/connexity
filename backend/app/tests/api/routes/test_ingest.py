"""Ingest tokens and the ingest endpoint."""

import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, func, select

from app import crud
from app.core.config import settings
from app.core.db import engine
from app.models import Call, IngestToken
from app.models.call import CallEvent
from app.models.enums import TraceCapability
from app.tests.traces.examples import EXAMPLE_NAMES, load_example, load_example_json
from app.tests.utils.utils import extract_cookies, random_email, random_lower_string

TOKENS = f"{settings.API_V1_STR}/ingest-tokens"
INGEST = f"{settings.API_V1_STR}/ingest/traces"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_token(client: TestClient, cookies: dict[str, str]) -> dict[str, str]:
    r = client.post(f"{TOKENS}/", json={"name": "webhook"}, cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json()


def _create_agent(client: TestClient, cookies: dict[str, str]) -> str:
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json={
            "name": f"agent-{uuid.uuid4().hex[:6]}",
            "endpoint_url": "http://example.com/agent",
        },
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _other_company_cookies(client: TestClient) -> dict[str, str]:
    email, password = random_email(), random_lower_string()
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return extract_cookies(r)


def _send(
    client: TestClient, token: str, agent_id: str, trace: dict[str, object]
) -> dict[str, object]:
    r = client.post(
        INGEST, json={"agent_id": agent_id, "trace": trace}, headers=_bearer(token)
    )
    assert r.status_code == 200, r.text
    return r.json()


# ── Tokens ─────────────────────────────────────────────────────────


def test_token_secret_is_returned_once_and_never_stored(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    created = _create_token(client, auth_cookies)
    secret = created["token"]
    assert secret.startswith("cxi_")
    assert created["prefix"] == secret[:12]

    listed = client.get(f"{TOKENS}/", cookies=auth_cookies).json()
    row = next(item for item in listed["data"] if item["id"] == created["id"])
    assert "token" not in row
    assert row["revoked_at"] is None

    stored = db.get(IngestToken, uuid.UUID(created["id"]))
    assert stored is not None
    assert secret not in (stored.token_hash, stored.prefix, stored.name)
    assert len(stored.token_hash) == 64


def test_tokens_require_login(client: TestClient) -> None:
    assert client.get(f"{TOKENS}/").status_code == 401
    assert client.post(f"{TOKENS}/", json={"name": "x"}).status_code == 401


def test_tokens_are_scoped_to_the_company(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    created = _create_token(client, auth_cookies)
    other = _other_company_cookies(client)

    listed = client.get(f"{TOKENS}/", cookies=other).json()
    assert created["id"] not in [item["id"] for item in listed["data"]]
    assert client.delete(f"{TOKENS}/{created['id']}", cookies=other).status_code == 404


def test_revoked_token_stops_working_and_stays_listed(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    created = _create_token(client, auth_cookies)
    agent_id = _create_agent(client, auth_cookies)
    _send(
        client, created["token"], agent_id, load_example_json("self-hosted-text-only")
    )

    r = client.delete(f"{TOKENS}/{created['id']}", cookies=auth_cookies)
    assert r.status_code == 200

    r = client.post(
        INGEST,
        json={
            "agent_id": agent_id,
            "trace": load_example_json("self-hosted-text-only"),
        },
        headers=_bearer(created["token"]),
    )
    assert r.status_code == 401

    listed = client.get(f"{TOKENS}/", cookies=auth_cookies).json()
    row = next(item for item in listed["data"] if item["id"] == created["id"])
    assert row["revoked_at"] is not None
    assert row["last_used_at"] is not None


# ── Ingest ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_ingest_stores_each_published_example(
    client: TestClient, auth_cookies: dict[str, str], db: Session, name: str
) -> None:
    token = _create_token(client, auth_cookies)["token"]
    agent_id = _create_agent(client, auth_cookies)

    result = _send(client, token, agent_id, load_example_json(name))

    assert result["created"] is True
    call = db.get(Call, uuid.UUID(str(result["call_id"])))
    assert call is not None
    assert str(call.agent_id) == agent_id
    assert crud.get_trace(session=db, call=call) == load_example(name)


def test_ingest_reports_capabilities_and_what_is_missing(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    token = _create_token(client, auth_cookies)["token"]
    agent_id = _create_agent(client, auth_cookies)

    full = _send(client, token, agent_id, load_example_json("hosted-platform-full"))
    assert set(full["capabilities"]) == {c.value for c in TraceCapability}
    assert full["missing_capabilities"] == []

    bare = _send(client, token, agent_id, load_example_json("self-hosted-text-only"))
    assert bare["capabilities"] == []
    assert set(bare["missing_capabilities"]) == {c.value for c in TraceCapability}


def test_resending_a_call_replaces_its_trace(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    token = _create_token(client, auth_cookies)["token"]
    agent_id = _create_agent(client, auth_cookies)
    first = load_example_json("hosted-platform-full")
    second = {**first, "events": first["events"][:2], "end_reason": "caller_hangup"}  # type: ignore[index]

    created = _send(client, token, agent_id, first)
    replaced = _send(client, token, agent_id, second)

    assert created["created"] is True
    assert replaced["created"] is False
    assert replaced["call_id"] == created["call_id"]
    call = db.get(Call, uuid.UUID(str(created["call_id"])))
    assert call is not None
    db.refresh(call)
    trace = crud.get_trace(session=db, call=call)
    assert trace is not None
    assert len(trace.events) == 2
    assert trace.end_reason == "caller_hangup"


def test_ingest_stores_the_original_payload_when_sent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    token = _create_token(client, auth_cookies)["token"]
    agent_id = _create_agent(client, auth_cookies)
    raw = {"call_id": "abc", "nested": {"anything": [1, 2, 3]}}

    r = client.post(
        INGEST,
        json={
            "agent_id": agent_id,
            "trace": load_example_json("self-hosted-text-only"),
            "raw": raw,
        },
        headers=_bearer(token),
    )
    assert r.status_code == 200, r.text
    call = db.get(Call, uuid.UUID(r.json()["call_id"]))
    assert call is not None
    assert call.raw == raw


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer "},
        {"Authorization": "Bearer cxi_not-a-real-token"},
        {"Authorization": "Basic abc"},
    ],
)
def test_ingest_refuses_a_bad_token_without_saying_why(
    client: TestClient, auth_cookies: dict[str, str], headers: dict[str, str]
) -> None:
    agent_id = _create_agent(client, auth_cookies)
    r = client.post(
        INGEST,
        json={
            "agent_id": agent_id,
            "trace": load_example_json("self-hosted-text-only"),
        },
        headers=headers,
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Missing or invalid ingest token"


def test_login_cookie_is_not_an_ingest_credential(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    agent_id = _create_agent(client, auth_cookies)
    r = client.post(
        INGEST,
        json={
            "agent_id": agent_id,
            "trace": load_example_json("self-hosted-text-only"),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 401


def test_token_cannot_write_to_another_companys_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    token = _create_token(client, auth_cookies)["token"]
    other_agent = _create_agent(client, _other_company_cookies(client))
    body = {
        "agent_id": other_agent,
        "trace": load_example_json("self-hosted-text-only"),
    }

    foreign = client.post(INGEST, json=body, headers=_bearer(token))
    missing = client.post(
        INGEST, json={**body, "agent_id": str(uuid.uuid4())}, headers=_bearer(token)
    )

    assert foreign.status_code == 404
    assert foreign.json() == missing.json()
    count = db.exec(
        select(func.count())
        .select_from(Call)
        .where(Call.agent_id == uuid.UUID(other_agent))
    ).one()
    assert count == 0


def test_invalid_trace_is_refused_and_the_field_is_named(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    token = _create_token(client, auth_cookies)["token"]
    agent_id = _create_agent(client, auth_cookies)
    trace = load_example_json("self-hosted-text-only")
    trace["events"][0]["speaker"] = "robot"  # type: ignore[index]

    r = client.post(
        INGEST, json={"agent_id": agent_id, "trace": trace}, headers=_bearer(token)
    )

    assert r.status_code == 422
    assert "speaker" in r.text


def test_trace_with_too_many_events_is_refused(
    client: TestClient, auth_cookies: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "INGEST_MAX_EVENTS", 2)
    token = _create_token(client, auth_cookies)["token"]
    agent_id = _create_agent(client, auth_cookies)

    r = client.post(
        INGEST,
        json={
            "agent_id": agent_id,
            "trace": load_example_json("self-hosted-text-only"),
        },
        headers=_bearer(token),
    )

    assert r.status_code == 422
    assert "limit is 2" in r.json()["detail"]


def test_oversized_body_is_refused(
    client: TestClient, auth_cookies: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "INGEST_MAX_BODY_BYTES", 200)
    token = _create_token(client, auth_cookies)["token"]
    agent_id = _create_agent(client, auth_cookies)

    r = client.post(
        INGEST,
        json={"agent_id": agent_id, "trace": load_example_json("hosted-platform-full")},
        headers=_bearer(token),
    )

    assert r.status_code == 413


def test_oversized_body_from_an_unauthenticated_caller_is_401_not_413(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "INGEST_MAX_BODY_BYTES", 10)
    r = client.post(
        INGEST,
        json={
            "agent_id": str(uuid.uuid4()),
            "trace": load_example_json("hosted-platform-full"),
        },
    )
    assert r.status_code == 401


def test_two_simultaneous_stores_of_a_new_call_both_succeed(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = uuid.UUID(_create_agent(client, auth_cookies))
    agent = crud.get_agent(session=db, agent_id=agent_id)
    assert agent is not None
    trace = load_example("hosted-platform-full")
    start = threading.Barrier(2)
    created: list[bool] = []
    errors: list[BaseException] = []

    def store() -> None:
        try:
            with Session(engine) as session:
                start.wait(timeout=10)
                stored = crud.store_trace(
                    session=session,
                    trace=trace,
                    agent_id=agent_id,
                    company_id=agent.company_id,
                )
                created.append(stored.created)
        except BaseException as exc:  # noqa: BLE001 - reported by the assert below
            errors.append(exc)

    threads = [threading.Thread(target=store) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert errors == []
    assert sorted(created) == [False, True]
    calls = db.exec(select(Call).where(Call.agent_id == agent_id)).all()
    assert len(calls) == 1
    events = db.exec(
        select(func.count())
        .select_from(CallEvent)
        .where(col(CallEvent.call_id) == calls[0].id)
    ).one()
    assert events == len(trace.events)
