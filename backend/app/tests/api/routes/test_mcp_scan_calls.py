"""The first scan through MCP. Every Retell answer here is invented."""

import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
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
from app.core.encryption import encrypt, mask_key
from app.models import Agent, Call, User, UserCreate
from app.models.enums import IntegrationProvider, Platform
from app.models.integration import Integration
from app.services import first_scan
from app.services.mappings.retell import retell_call_to_trace
from app.tests.utils.retell_payloads import retell_call
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
MCP_URL = "https://mcp.example.com/mcp"
ISSUER = "https://backend.example.com"
LIST_CALLS = "https://api.retellai.com/v3/list-calls"
LIST_AGENTS = "https://api.retellai.com/v2/list-agents"
GET_CALL = r"https://api.retellai.com/v2/get-call/(?P<call_id>[^/]+)"
GET_AGENT = r"https://api.retellai.com/get-agent/.+"
# Versions are read from the invented Retell account below.
pytestmark = pytest.mark.provider_versions

NOW_MS = int(datetime.now(UTC).timestamp() * 1000)
HOUR_MS = 3_600_000


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    # One page of two calls per step.
    monkeypatch.setattr(first_scan, "STEP_SECONDS", 0.0)
    monkeypatch.setattr(first_scan, "READ_PAGE", 2)
    yield
    encryption._fernet.cache_clear()


class RetellAccount:
    """An invented Retell account: a call list and full call records."""

    def __init__(self, calls: list[dict[str, Any]]) -> None:
        self.calls = sorted(calls, key=lambda c: c["start_timestamp"])
        self.read: list[str] = []
        self.fail_reading: set[str] = set()
        self.refused: set[str] = set()

    def list_calls(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        after = body["filter_criteria"]["start_timestamp"]["value"]
        agent = body["filter_criteria"]["agent"][0]["agent_id"]
        items = [
            {k: v for k, v in c.items() if k != "transcript_with_tool_calls"}
            for c in self.calls
            if c["start_timestamp"] > after and c["agent_id"] == agent
        ][: body["limit"]]
        return httpx.Response(200, json={"items": items})

    def get_call(self, request: httpx.Request, call_id: str) -> httpx.Response:
        if call_id in self.fail_reading:
            return httpx.Response(500, json={})
        if call_id in self.refused:
            return httpx.Response(400, json={})
        self.read.append(call_id)
        found = next((c for c in self.calls if c["call_id"] == call_id), None)
        if found is None:
            return httpx.Response(404, json={})
        return httpx.Response(200, json=found)

    def mock(self, *, versions: bool = True) -> None:
        respx.post(LIST_CALLS).mock(side_effect=self.list_calls)
        respx.get(url__regex=GET_CALL).mock(side_effect=self.get_call)
        respx.get(url__regex=GET_AGENT).mock(
            return_value=httpx.Response(200, json={"agent_id": "agent_scan"})
            if versions
            else httpx.Response(404, json={})
        )


def _call(call_id: str, hours_ago: float, **overrides: Any) -> dict[str, Any]:
    return retell_call(
        call_id,
        agent_id=overrides.pop("agent_id", "agent_scan"),
        start_ms=NOW_MS - int(hours_ago * HOUR_MS),
        **overrides,
    )


def _five_calls_and_two_outside() -> list[dict[str, Any]]:
    return [
        _call("call_old", 24 * 40),  # before the 30-day window
        *[_call(f"call_{i}", 24 * 20 - i) for i in range(5)],
        _call("call_ongoing", 0.1, call_status="ongoing", end_timestamp=None),
    ]


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


def _connect(db: Session, user: User) -> Integration:
    integration = Integration(
        provider=IntegrationProvider.RETELL,
        name="Retell",
        company_id=user.company_id,
        encrypted_api_key=encrypt("key_invented_scan"),
        masked_api_key=mask_key("key_invented_scan"),
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def _add(
    db: Session, user: User, integration: Integration, platform_id: str = "agent_scan"
) -> Agent:
    agent, _ = crud.add_platform_agent(
        session=db,
        company_id=user.company_id,
        integration=integration,
        platform=Platform.RETELL,
        platform_agent_id=platform_id,
        name=f"Agent {platform_id}",
        platform_agent_name=None,
        created_by=user.id,
    )
    return agent


def _scan(client: TestClient, user: User) -> httpx.Response:
    return client.post(
        f"{API}/mcp/workspaces/{user.company_id}/scan", headers=_headers(user)
    )


def _readiness(client: TestClient, user: User) -> dict[str, Any]:
    return client.get(
        f"{API}/mcp/workspaces/{user.company_id}/readiness", headers=_headers(user)
    ).json()


def _scan_to_the_end(client: TestClient, user: User) -> dict[str, Any]:
    for _ in range(20):
        r = _scan(client, user)
        assert r.status_code == 200, r.text
        if r.json()["data"]["finished"]:
            return r.json()
    raise AssertionError("the scan did not finish")


def _stored(db: Session, agent: Agent) -> list[str]:
    db.expire_all()
    return sorted(
        db.exec(select(Call.external_id).where(Call.agent_id == agent.id)).all()
    )


@respx.mock
def test_the_scan_brings_in_the_window_in_steps(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _add(db, user, _connect(db, user))
    RetellAccount(_five_calls_and_two_outside()).mock()

    # With no time left, the first step only counts the window.
    counted = _scan(client, user)

    assert counted.status_code == 200, counted.text
    assert counted.json()["data"]["stored_this_step"] == 0
    assert counted.json()["data"]["agents"][0]["total"] == 5

    first = _scan(client, user)

    body = first.json()
    assert body["data"]["finished"] is False
    assert body["data"]["stored_this_step"] == 2
    assert body["data"]["agents"][0] | {"agent_id": None} == {
        "agent_id": None,
        "name": "Agent agent_scan",
        "stored": 2,
        "total": 5,
        "finished": False,
    }
    assert "Call `scan_calls` again: 2 of 5 calls" in body["next_steps"][0]
    step3 = _readiness(client, user)["data"]["steps"][2]
    assert (step3["state"], step3["detail"]) == (
        "in_progress",
        "2 of 5 calls · 0 of 1 agent",
    )

    last = _scan_to_the_end(client, user)

    assert _stored(db, agent) == [f"call_{i}" for i in range(5)]
    assert last["data"]["agents"][0]["stored"] == 5
    assert last["data"]["calls_without_versions"] == 0
    assert any(
        "first scan is finished: 5 calls from 1 agent are" in s
        for s in last["next_steps"]
    )
    readiness = _readiness(client, user)
    steps = readiness["data"]["steps"]
    assert (steps[2]["state"], steps[2]["detail"]) == ("done", "1 agent · 5 calls")
    assert (steps[3]["state"], steps[3]["detail"]) == (
        "done",
        "5 calls across 1 agent",
    )
    assert readiness["data"]["first_scan_done"] is True
    assert not any("scan_calls" in s for s in readiness["next_steps"])


@respx.mock
def test_a_finished_scan_answers_at_once(client: TestClient, db: Session) -> None:
    user = _person(db)
    _add(db, user, _connect(db, user))
    RetellAccount([_call("call_0", 5)]).mock()
    _scan_to_the_end(client, user)
    calls_before = len(respx.calls)

    r = _scan(client, user)

    assert r.status_code == 200
    assert r.json()["data"]["finished"] is True
    assert r.json()["data"]["stored_this_step"] == 0
    assert len(respx.calls) == calls_before


@respx.mock
def test_calls_already_stored_are_not_read_again(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    integration = _connect(db, user)
    agent = _add(db, user, integration)
    calls = _five_calls_and_two_outside()
    account = RetellAccount(calls)
    account.mock()
    # The webhook stored one call before the scan began.
    crud.store_trace(
        session=db,
        trace=retell_call_to_trace(calls[2]),
        agent_id=agent.id,
        company_id=user.company_id,
        integration_id=integration.id,
        raw=calls[2],
    )
    db.commit()

    _scan_to_the_end(client, user)

    assert calls[2]["call_id"] not in account.read
    assert _stored(db, agent) == [f"call_{i}" for i in range(5)]


@respx.mock
def test_retell_failing_mid_scan_keeps_what_was_stored(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _add(db, user, _connect(db, user))
    account = RetellAccount(_five_calls_and_two_outside())
    account.mock()
    respx.post(LIST_AGENTS).mock(return_value=httpx.Response(200, json={"items": []}))
    assert _scan(client, user).status_code == 200  # counts
    assert _scan(client, user).status_code == 200  # call_0, call_1
    account.fail_reading = {"call_2"}

    r = _scan(client, user)

    assert r.status_code == 503
    detail = r.json()["detail"]
    assert detail["error"] == "Retell could not be reached during the scan"
    assert any("carries on where it stopped" in s for s in detail["next_steps"])
    assert _stored(db, agent) == ["call_0", "call_1"]

    account.fail_reading = set()
    _scan_to_the_end(client, user)
    assert _stored(db, agent) == [f"call_{i}" for i in range(5)]


@respx.mock
def test_a_revoked_key_asks_to_reconnect(client: TestClient, db: Session) -> None:
    user = _person(db)
    _add(db, user, _connect(db, user))
    respx.post(LIST_CALLS).mock(return_value=httpx.Response(401, json={}))
    respx.post(LIST_AGENTS).mock(return_value=httpx.Response(401, json={}))

    r = _scan(client, user)

    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["error"] == "Retell refused the key stored for this workspace"
    assert any("connect_voice_platform" in s for s in detail["next_steps"])


def test_without_agents_the_next_step_is_add_agents(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    _connect(db, user)

    r = _scan(client, user)

    assert r.status_code == 409
    assert any("add_agents" in s for s in r.json()["detail"]["next_steps"])


def test_another_workspace_is_not_found(client: TestClient, db: Session) -> None:
    user = _person(db)
    other = _person(db)
    _add(db, other, _connect(db, other))

    r = client.post(
        f"{API}/mcp/workspaces/{other.company_id}/scan", headers=_headers(user)
    )

    assert r.status_code == 404


@respx.mock
def test_an_agent_added_after_the_first_scan(client: TestClient, db: Session) -> None:
    user = _person(db)
    integration = _connect(db, user)
    _add(db, user, integration)
    RetellAccount(
        [_call("call_a", 5), _call("call_b", 4, agent_id="agent_later")]
    ).mock()
    _scan_to_the_end(client, user)
    later = _add(db, user, integration, "agent_later")

    steps = _readiness(client, user)["data"]["steps"]
    assert steps[2]["state"] == "in_progress"
    assert steps[3]["state"] == "done"
    assert any("scan_calls" in s for s in _readiness(client, user)["next_steps"])

    _scan_to_the_end(client, user)

    assert _stored(db, later) == ["call_b"]
    assert _readiness(client, user)["data"]["steps"][2]["state"] == "done"


@respx.mock
def test_calls_whose_versions_retell_no_longer_has_are_counted(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    _add(db, user, _connect(db, user))
    RetellAccount([_call("call_0", 5), _call("call_1", 4)]).mock(versions=False)

    last = _scan_to_the_end(client, user)

    assert last["data"]["calls_without_versions"] == 2
    assert any("no resolved agent version" in s for s in last["next_steps"])
    step4 = _readiness(client, user)["data"]["steps"][3]
    assert step4["detail"] == "2 calls across 1 agent · 2 calls without versions"


@respx.mock
def test_add_agents_and_readiness_name_the_scan(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    _connect(db, user)
    respx.post(LIST_AGENTS).mock(
        return_value=httpx.Response(
            200,
            json={"items": [{"agent_id": "agent_scan", "agent_name": "Front desk"}]},
        )
    )

    added = client.post(
        f"{API}/mcp/workspaces/{user.company_id}/agents",
        headers=_headers(user),
        json={"agents": [{"platform_agent_id": "agent_scan"}]},
    ).json()

    assert any("scan_calls" in s for s in added["next_steps"])
    assert any("scan_calls" in s for s in _readiness(client, user)["next_steps"])


@respx.mock
def test_calls_that_started_in_the_same_millisecond_are_all_stored(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _add(db, user, _connect(db, user))
    same = NOW_MS - 5 * HOUR_MS
    RetellAccount(
        [
            _call("call_first", 6),
            retell_call("call_same_a", agent_id="agent_scan", start_ms=same),
            retell_call("call_same_b", agent_id="agent_scan", start_ms=same),
            _call("call_last", 4),
        ]
    ).mock()

    last = _scan_to_the_end(client, user)

    assert _stored(db, agent) == sorted(
        ["call_first", "call_same_a", "call_same_b", "call_last"]
    )
    assert last["data"]["agents"][0]["total"] == 4


@respx.mock
def test_a_call_retell_refuses_to_return_is_passed_over(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _add(db, user, _connect(db, user))
    account = RetellAccount(
        [_call("call_0", 6), _call("call_bad", 5), _call("call_2", 4)]
    )
    account.refused = {"call_bad"}
    account.mock()

    _scan_to_the_end(client, user)

    assert _stored(db, agent) == ["call_0", "call_2"]


def test_without_retell_agents_readiness_does_not_ask_for_a_scan(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    integration = _connect(db, user)
    agent = _add(db, user, integration)
    agent.platform = Platform.VAPI
    db.add(agent)
    db.commit()

    assert not any("scan_calls" in s for s in _readiness(client, user)["next_steps"])
