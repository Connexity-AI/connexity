"""Tool-to-workflow mapping, and a tool call opening to its execution.

Every Retell and n8n payload here is invented.
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core import encryption
from app.core.config import settings
from app.models import Agent, AgentToolBackend, Call, CallExecution
from app.models.enums import Platform
from app.services import executions as executions_service
from app.services.mappings.retell import retell_call_to_trace
from app.services.n8n import (
    N8nConnectionResult,
    N8nError,
    N8nExecutionSummary,
    N8nWorkflow,
)
from app.services.retell import RetellCall
from app.tests.utils.n8n_payloads import n8n_execution
from app.tests.utils.retell_payloads import (
    START_MS,
    invocation,
    result,
    retell_call,
    speech,
)
from app.tests.utils.utils import extract_cookies, random_email, random_lower_string

API = settings.API_V1_STR
N8N_URL = "https://n8n.example.com"
CALL_START = datetime.fromtimestamp(START_MS / 1000, tz=UTC)
WORKFLOW = N8nWorkflow(id="wf_invented_1", name="Invented price lookup", active=True)


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    yield
    encryption._fernet.cache_clear()


def _agent(client: TestClient, cookies: dict[str, str], db: Session) -> Agent:
    r = client.post(
        f"{API}/agents/",
        json={
            "name": f"agent-{uuid.uuid4().hex[:6]}",
            "endpoint_url": "http://example.com/agent",
        },
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    agent = db.get(Agent, uuid.UUID(r.json()["id"]))
    assert agent is not None
    agent.platform = Platform.RETELL
    agent.platform_agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _n8n(client: TestClient, cookies: dict[str, str]) -> str:
    ok = AsyncMock(return_value=N8nConnectionResult(ok=True, base_url=N8N_URL))
    with patch("app.api.routes.integrations.check_n8n_connection", ok):
        r = client.post(
            f"{API}/integrations/",
            json={
                "provider": "n8n",
                "name": f"n8n-{uuid.uuid4().hex[:6]}",
                "api_key": "n8n_api_invented_key",
                "base_url": N8N_URL,
            },
            cookies=cookies,
        )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _map(
    client: TestClient,
    cookies: dict[str, str],
    agent_id: uuid.UUID,
    integration_id: str,
    tool_name: str = "get_price",
    workflow: N8nWorkflow | None = WORKFLOW,
) -> Any:
    with patch(
        "app.api.routes.tool_backends.get_n8n_workflow",
        AsyncMock(return_value=workflow),
    ):
        return client.put(
            f"{API}/agents/{agent_id}/tool-backends",
            json={
                "tool_name": tool_name,
                "integration_id": integration_id,
                "workflow_id": "wf_invented_1",
            },
            cookies=cookies,
        )


def _other_company(client: TestClient) -> dict[str, str]:
    email, password = random_email(), random_lower_string()
    client.post(f"{API}/users/signup", json={"email": email, "password": password})
    login = client.post(
        f"{API}/login/access-token", data={"username": email, "password": password}
    )
    assert login.status_code == 200, login.text
    return extract_cookies(login)


def _store_call(
    db: Session,
    agent: Agent,
    timeline: list[dict[str, Any]],
    call_id: str | None = None,
) -> Call:
    payload = retell_call(
        call_id or f"call_{uuid.uuid4().hex[:10]}",
        agent_id=agent.platform_agent_id or "",
        timeline=timeline,
    )
    return crud.store_trace(
        session=db,
        trace=retell_call_to_trace(payload),
        agent_id=agent.id,
        company_id=agent.company_id,
        raw=payload,
    ).call


def _price_call(tool_call_id: str, at_sec: float, args: str = '{"sku": "A-1"}'):
    return [
        invocation(tool_call_id, "get_price", args, time_sec=at_sec),
        result(tool_call_id, '{"price": 120}', successful=True, time_sec=at_sec + 1),
    ]


def _n8n_answers(executions: list[dict[str, Any]]) -> tuple[AsyncMock, AsyncMock]:
    """Stand-ins for the two n8n reads, answering from ``executions``."""
    by_id = {str(e["id"]): e for e in executions}
    listing = AsyncMock(
        return_value=[
            N8nExecutionSummary(
                id=str(e["id"]),
                workflow_id=e["workflowId"],
                started_at=datetime.fromisoformat(
                    e["startedAt"].replace("Z", "+00:00")
                ),
            )
            for e in executions
        ]
    )
    detail = AsyncMock(side_effect=lambda _url, _key, execution_id: by_id[execution_id])
    return listing, detail


def _refresh(
    client: TestClient,
    cookies: dict[str, str],
    call: Call,
    executions: list[dict[str, Any]],
) -> tuple[dict[str, Any], AsyncMock, AsyncMock]:
    listing, detail = _n8n_answers(executions)
    with (
        patch("app.services.executions.list_n8n_executions", listing),
        patch("app.services.executions.get_n8n_execution", detail),
    ):
        r = client.post(f"{API}/calls/{call.id}/executions/refresh", cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json(), listing, detail


def _trace(client: TestClient, cookies: dict[str, str], call: Call) -> dict[str, Any]:
    r = client.get(f"{API}/calls/{call.id}/trace", cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json()


# ── Mapping a tool to a workflow ───────────────────────────────────


def test_tools_seen_in_calls_are_listed_and_can_be_mapped_changed_and_cleared(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    integration_id = _n8n(client, auth_cookies)
    _store_call(
        db,
        agent,
        [
            *_price_call("tc_1", 3.0),
            *_price_call("tc_2", 9.0),
            invocation("tc_end", "end_call", "", time_sec=20.0),
        ],
    )

    tools = client.get(f"{API}/agents/{agent.id}/tools", cookies=auth_cookies).json()
    assert tools == [
        {"name": "end_call", "call_count": 1, "backend": None},
        {"name": "get_price", "call_count": 2, "backend": None},
    ]

    r = _map(client, auth_cookies, agent.id, integration_id)
    assert r.status_code == 200, r.text
    assert r.json()["workflow_name"] == "Invented price lookup"
    renamed = N8nWorkflow(id="wf_invented_1", name="Renamed")
    assert (
        _map(client, auth_cookies, agent.id, integration_id, workflow=renamed).json()[
            "workflow_name"
        ]
        == "Renamed"
    )
    # A mapped tool is listed even if no stored call used it.
    assert (
        _map(client, auth_cookies, agent.id, integration_id, "never_called").status_code
        == 200
    )

    tools = client.get(f"{API}/agents/{agent.id}/tools", cookies=auth_cookies).json()
    assert [(t["name"], t["call_count"], bool(t["backend"])) for t in tools] == [
        ("end_call", 1, False),
        ("get_price", 2, True),
        ("never_called", 0, True),
    ]
    assert "n8n_api_invented_key" not in str(tools)

    cleared = client.delete(
        f"{API}/agents/{agent.id}/tool-backends",
        params={"tool_name": "get_price"},
        cookies=auth_cookies,
    )
    assert cleared.status_code == 200
    again = client.delete(
        f"{API}/agents/{agent.id}/tool-backends",
        params={"tool_name": "get_price"},
        cookies=auth_cookies,
    )
    assert again.status_code == 404


def test_mapping_is_refused_for_a_missing_workflow_a_voice_account_or_a_dead_n8n(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    integration_id = _n8n(client, auth_cookies)
    assert (
        _map(client, auth_cookies, agent.id, integration_id, workflow=None).status_code
        == 404
    )

    with patch(
        "app.api.routes.tool_backends.get_n8n_workflow",
        AsyncMock(side_effect=N8nError("Could not reach n8n")),
    ):
        r = client.put(
            f"{API}/agents/{agent.id}/tool-backends",
            json={
                "tool_name": "get_price",
                "integration_id": integration_id,
                "workflow_id": "wf_invented_1",
            },
            cookies=auth_cookies,
        )
    assert r.status_code == 502

    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {"retell": AsyncMock(return_value=True)},
        clear=False,
    ):
        retell_id = client.post(
            f"{API}/integrations/",
            json={"provider": "retell", "name": "retell", "api_key": "key_invented_1"},
            cookies=auth_cookies,
        ).json()["id"]
    assert _map(client, auth_cookies, agent.id, retell_id).status_code == 400
    assert (
        db.exec(
            select(AgentToolBackend).where(AgentToolBackend.agent_id == agent.id)
        ).all()
        == []
    )


def test_another_company_cannot_map_list_or_read_workflows(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    mine = _n8n(client, auth_cookies)
    other = _other_company(client)
    theirs = _n8n(client, other)

    # My agent with their connection; their login on my agent and my connection.
    assert _map(client, auth_cookies, agent.id, theirs).status_code == 404
    assert _map(client, other, agent.id, theirs).status_code == 404
    assert (
        client.get(f"{API}/agents/{agent.id}/tools", cookies=other).status_code == 404
    )
    listing = AsyncMock(return_value=[WORKFLOW])
    with patch("app.api.routes.integrations.list_n8n_workflows", listing):
        assert (
            client.get(
                f"{API}/integrations/{mine}/workflows", cookies=other
            ).status_code
            == 404
        )
        mine_r = client.get(
            f"{API}/integrations/{mine}/workflows", cookies=auth_cookies
        )
    assert mine_r.status_code == 200
    assert mine_r.json() == [
        {"id": "wf_invented_1", "name": "Invented price lookup", "active": True}
    ]
    assert listing.await_count == 1
    assert client.get(f"{API}/agents/{agent.id}/tools").status_code == 401


def test_workflows_of_a_voice_account_or_an_unreachable_n8n(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    integration_id = _n8n(client, auth_cookies)
    with patch(
        "app.api.routes.integrations.list_n8n_workflows",
        AsyncMock(side_effect=N8nError("Could not reach n8n")),
    ):
        r = client.get(
            f"{API}/integrations/{integration_id}/workflows", cookies=auth_cookies
        )
    assert r.status_code == 502


def test_deleting_the_connection_removes_its_mappings(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    integration_id = _n8n(client, auth_cookies)
    assert _map(client, auth_cookies, agent.id, integration_id).status_code == 200
    r = client.delete(f"{API}/integrations/{integration_id}", cookies=auth_cookies)
    assert r.status_code == 200, r.text
    db.expire_all()
    assert (
        db.exec(
            select(AgentToolBackend).where(AgentToolBackend.agent_id == agent.id)
        ).all()
        == []
    )


# ── A tool call opens to its execution ─────────────────────────────


def test_an_execution_is_matched_by_call_id_tool_and_arguments(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    assert (
        _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies)).status_code
        == 200
    )
    call = _store_call(
        db,
        agent,
        [
            speech("user", "What is the price", 1.0),
            *_price_call("tc_1", 3.0),
            invocation("tc_end", "end_call", "", time_sec=20.0),
        ],
    )
    mine = n8n_execution(
        "9001", started_at=CALL_START + timedelta(seconds=3.2), call_id=call.external_id
    )
    someone_elses = n8n_execution(
        "9002", started_at=CALL_START + timedelta(seconds=3.1), call_id="call_other"
    )
    other_arguments = n8n_execution(
        "9003",
        started_at=CALL_START + timedelta(seconds=3.3),
        call_id=call.external_id,
        args={"sku": "Z-9"},
    )

    summary, listing, _detail = _refresh(
        client, auth_cookies, call, [someone_elses, other_arguments, mine]
    )

    assert summary == {"tool_calls": 2, "mapped": 1, "matched": 1, "problems": []}
    # One question to n8n: this workflow, during this call.
    assert listing.await_count == 1
    asked = listing.await_args.kwargs
    assert asked["workflow_id"] == "wf_invented_1"
    assert asked["started_after"] < CALL_START < asked["started_before"]

    body = _trace(client, auth_cookies, call)
    (execution,) = body["executions"]
    assert execution["event_id"] == "tc_1"
    assert execution["external_id"] == "9001"
    assert execution["match"] == "exact"
    assert execution["status"] == "ok"
    assert execution["workflow_name"] == "Invented price lookup"
    assert [s["name"] for s in execution["steps"]] == ["Webhook", "Look up", "Respond"]
    assert execution["steps"][0]["output"] == {
        "name": "get_price",
        "arguments": {"sku": "A-1"},
    }
    assert execution["steps"][2]["input_from"] == ["Look up"]
    assert "x-retell-signature" not in str(body)


def test_two_identical_tool_calls_each_get_their_own_execution(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies))
    call = _store_call(
        db, agent, [*_price_call("tc_a", 3.0), *_price_call("tc_b", 30.0)]
    )
    first = n8n_execution(
        "9101", started_at=CALL_START + timedelta(seconds=3.1), call_id=call.external_id
    )
    second = n8n_execution(
        "9102",
        started_at=CALL_START + timedelta(seconds=30.1),
        call_id=call.external_id,
    )

    summary, _l, _d = _refresh(client, auth_cookies, call, [second, first])

    assert summary["matched"] == 2
    paired = {
        e["event_id"]: e["external_id"]
        for e in _trace(client, auth_cookies, call)["executions"]
    }
    assert paired == {"tc_a": "9101", "tc_b": "9102"}


def test_a_trigger_without_a_call_id_is_matched_as_a_guess(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies))
    call = _store_call(db, agent, _price_call("tc_1", 3.0))
    near = n8n_execution(
        "9201", started_at=CALL_START + timedelta(seconds=3.4), call_id=None
    )
    far = n8n_execution(
        "9202", started_at=CALL_START + timedelta(seconds=25), call_id=None
    )

    summary, _l, _d = _refresh(client, auth_cookies, call, [far, near])

    assert summary["matched"] == 1
    (execution,) = _trace(client, auth_cookies, call)["executions"]
    assert (execution["external_id"], execution["match"]) == ("9201", "guess")
    assert execution["steps"][0]["output"] == {"arguments": {"sku": "A-1"}}


def test_a_failed_node_shows_as_failed_with_its_error(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies))
    call = _store_call(db, agent, _price_call("tc_1", 3.0))
    failed = n8n_execution(
        "9301",
        started_at=CALL_START + timedelta(seconds=3.1),
        call_id=call.external_id,
        failing=True,
    )
    _refresh(client, auth_cookies, call, [failed])
    (execution,) = _trace(client, auth_cookies, call)["executions"]
    assert execution["status"] == "error"
    last = execution["steps"][-1]
    assert (last["name"], last["status"]) == ("Look up", "error")
    assert last["error"]["message"] == "Request failed with status code 500"
    assert "stack" not in last["error"]


def test_no_execution_and_unmapped_tools(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    call = _store_call(db, agent, _price_call("tc_1", 3.0))

    # Nothing mapped: n8n is not asked at all.
    summary, listing, _d = _refresh(client, auth_cookies, call, [])
    assert summary == {"tool_calls": 1, "mapped": 0, "matched": 0, "problems": []}
    assert listing.await_count == 0

    _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies))
    summary, listing, _d = _refresh(client, auth_cookies, call, [])
    assert summary == {"tool_calls": 1, "mapped": 1, "matched": 0, "problems": []}
    assert listing.await_count == 1
    assert _trace(client, auth_cookies, call)["executions"] == []


def test_looking_again_does_not_duplicate_and_replacing_the_trace_keeps_executions(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies))
    call = _store_call(db, agent, _price_call("tc_1", 3.0))
    execution = n8n_execution(
        "9401", started_at=CALL_START + timedelta(seconds=3.1), call_id=call.external_id
    )
    _refresh(client, auth_cookies, call, [execution])
    _refresh(client, auth_cookies, call, [execution])
    rows = db.exec(select(CallExecution).where(CallExecution.call_id == call.id)).all()
    assert len(rows) == 1

    # A later look that finds nothing leaves what was stored: n8n forgets, Connexity keeps.
    _refresh(client, auth_cookies, call, [])
    # The provider sends the call again and its trace is replaced.
    _store_call(
        db,
        agent,
        [speech("agent", "Hello", 0.5), *_price_call("tc_1", 3.0)],
        call_id=call.external_id,
    )
    body = _trace(client, auth_cookies, call)
    assert len(body["trace"]["events"]) == 2
    assert [e["external_id"] for e in body["executions"]] == ["9401"]


@pytest.mark.parametrize(
    "broken",
    [
        {"list": N8nError("Could not reach n8n")},
        {"detail": N8nError("n8n did not answer with JSON")},
        {"detail": [{"status": "success"}]},  # malformed: no id, no data
    ],
)
def test_a_slow_empty_or_malformed_n8n_is_reported_and_stores_nothing(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
    broken: dict[str, Any],
) -> None:
    agent = _agent(client, auth_cookies, db)
    _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies))
    call = _store_call(db, agent, _price_call("tc_1", 3.0))
    listing, detail = _n8n_answers(
        [
            n8n_execution(
                "9501",
                started_at=CALL_START + timedelta(seconds=3.1),
                call_id=call.external_id,
            )
        ]
    )
    if "list" in broken:
        listing.side_effect = broken["list"]
    else:
        detail.side_effect = broken["detail"]
    with (
        patch("app.services.executions.list_n8n_executions", listing),
        patch("app.services.executions.get_n8n_execution", detail),
    ):
        r = client.post(
            f"{API}/calls/{call.id}/executions/refresh", cookies=auth_cookies
        )
    assert r.status_code == 200, r.text
    assert r.json()["matched"] == 0
    assert _trace(client, auth_cookies, call)["executions"] == []


def test_executions_of_another_companys_call_are_not_found(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    call = _store_call(db, agent, _price_call("tc_1", 3.0))
    other = _other_company(client)
    assert (
        client.post(
            f"{API}/calls/{call.id}/executions/refresh", cookies=other
        ).status_code
        == 404
    )
    assert client.post(f"{API}/calls/{call.id}/executions/refresh").status_code == 401


# ── Looked for when a call arrives ─────────────────────────────────


def _link_retell(
    client: TestClient, cookies: dict[str, str], db: Session, agent: Agent
) -> None:
    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {"retell": AsyncMock(return_value=True)},
        clear=False,
    ):
        retell_id = client.post(
            f"{API}/integrations/",
            json={"provider": "retell", "name": "retell", "api_key": "key_invented_1"},
            cookies=cookies,
        ).json()["id"]
    agent.integration_id = uuid.UUID(retell_id)
    db.add(agent)
    db.commit()


@pytest.mark.parametrize("n8n_down", [False, True])
def test_a_pulled_call_gets_its_executions_and_is_stored_even_if_n8n_is_down(
    client: TestClient, auth_cookies: dict[str, str], db: Session, n8n_down: bool
) -> None:
    agent = _agent(client, auth_cookies, db)
    _link_retell(client, auth_cookies, db, agent)
    _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies))
    call_id = f"call_{uuid.uuid4().hex[:10]}"
    payload = retell_call(
        call_id,
        agent_id=agent.platform_agent_id or "",
        timeline=_price_call("tc_1", 3.0),
    )
    listing, detail = _n8n_answers(
        [
            n8n_execution(
                "9601", started_at=CALL_START + timedelta(seconds=3.1), call_id=call_id
            )
        ]
    )
    if n8n_down:
        listing.side_effect = RuntimeError("anything at all")
    with (
        patch(
            "app.services.call_sync.list_retell_calls",
            AsyncMock(
                return_value=[
                    RetellCall(call_id=call_id, start_timestamp=START_MS, raw=payload)
                ]
            ),
        ),
        patch("app.services.executions.list_n8n_executions", listing),
        patch("app.services.executions.get_n8n_execution", detail),
    ):
        first = client.post(
            f"{API}/agents/{agent.id}/calls/refresh", cookies=auth_cookies
        )
        second = client.post(
            f"{API}/agents/{agent.id}/calls/refresh", cookies=auth_cookies
        )
    assert first.status_code == 200, first.text
    assert (first.json()["created"], second.json()["created"]) == (1, 0)
    # Only a call seen for the first time is looked up.
    assert listing.await_count == 1

    call = db.exec(select(Call).where(Call.external_id == call_id)).one()
    executions = _trace(client, auth_cookies, call)["executions"]
    assert len(executions) == (0 if n8n_down else 1)


# ── Looked for without being asked ─────────────────────────────────


@pytest.fixture
def _calls_are_recent(monkeypatch: pytest.MonkeyPatch) -> None:
    # The invented calls carry a fixed, old start time.
    monkeypatch.setattr(settings, "EXECUTION_LOOKUP_MAX_AGE_DAYS", 100_000)
    executions_service._retry_not_before.clear()


def _open_calls_screen(
    client: TestClient,
    cookies: dict[str, str],
    db: Session,
    agent: Agent,
    listing: AsyncMock,
    detail: AsyncMock,
) -> None:
    db.refresh(agent)
    agent.calls_last_synced_at = None  # the list is stale: a sync is due
    db.add(agent)
    db.commit()
    with (
        patch("app.services.executions.list_n8n_executions", listing),
        patch("app.services.executions.get_n8n_execution", detail),
    ):
        r = client.get(f"{API}/agents/{agent.id}/calls", cookies=cookies)
    assert r.status_code == 200, r.text


@pytest.mark.usefixtures("_calls_are_recent")
def test_saving_or_changing_a_mapping_looks_up_the_tools_recent_calls(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    integration_id = _n8n(client, auth_cookies)
    call = _store_call(db, agent, _price_call("tc_1", 3.0))
    listing, detail = _n8n_answers(
        [
            n8n_execution(
                "9701",
                started_at=CALL_START + timedelta(seconds=3.1),
                call_id=call.external_id,
            )
        ]
    )
    with (
        patch("app.services.executions.list_n8n_executions", listing),
        patch("app.services.executions.get_n8n_execution", detail),
    ):
        assert _map(client, auth_cookies, agent.id, integration_id).status_code == 200
        # Nobody asked: the execution is there.
        (execution,) = _trace(client, auth_cookies, call)["executions"]
        assert execution["external_id"] == "9701"
        assert listing.await_count == 1

        # Pointing the tool at a workflow again makes its calls be looked up again.
        assert _map(client, auth_cookies, agent.id, integration_id).status_code == 200
        assert listing.await_count == 2
        # A mapping for another tool does not.
        assert (
            _map(
                client, auth_cookies, agent.id, integration_id, "other_tool"
            ).status_code
            == 200
        )
        assert listing.await_count == 2


@pytest.mark.usefixtures("_calls_are_recent")
def test_the_background_sync_looks_up_a_call_once(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    assert (
        _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies)).status_code
        == 200
    )
    call = _store_call(db, agent, _price_call("tc_1", 3.0))
    unmapped_only = _store_call(
        db, agent, [invocation("tc_e", "end_call", "", time_sec=5.0)]
    )
    listing, detail = _n8n_answers(
        [
            n8n_execution(
                "9801",
                started_at=CALL_START + timedelta(seconds=3.1),
                call_id=call.external_id,
            )
        ]
    )

    _open_calls_screen(client, auth_cookies, db, agent, listing, detail)
    assert listing.await_count == 1
    assert len(_trace(client, auth_cookies, call)["executions"]) == 1
    db.refresh(unmapped_only)
    assert unmapped_only.executions_checked_at is None  # nothing to ask about

    # Asked and answered: not asked again.
    _open_calls_screen(client, auth_cookies, db, agent, listing, detail)
    assert listing.await_count == 1


@pytest.mark.usefixtures("_calls_are_recent")
def test_a_lookup_that_failed_is_tried_again_after_the_wait(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    assert (
        _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies)).status_code
        == 200
    )
    call = _store_call(db, agent, _price_call("tc_1", 3.0))
    listing, detail = _n8n_answers(
        [
            n8n_execution(
                "9901",
                started_at=CALL_START + timedelta(seconds=3.1),
                call_id=call.external_id,
            )
        ]
    )
    down = AsyncMock(side_effect=N8nError("Could not reach n8n"))

    _open_calls_screen(client, auth_cookies, db, agent, down, detail)
    assert down.await_count == 1
    # n8n is back, but the wait is not over.
    _open_calls_screen(client, auth_cookies, db, agent, listing, detail)
    assert listing.await_count == 0
    assert _trace(client, auth_cookies, call)["executions"] == []

    executions_service._retry_not_before.clear()
    _open_calls_screen(client, auth_cookies, db, agent, listing, detail)
    assert listing.await_count == 1
    assert len(_trace(client, auth_cookies, call)["executions"]) == 1


def test_an_old_call_is_not_looked_up_on_its_own_but_is_on_request(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    executions_service._retry_not_before.clear()
    agent = _agent(client, auth_cookies, db)
    assert (
        _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies)).status_code
        == 200
    )
    # The invented call started long before the 30-day limit.
    call = _store_call(db, agent, _price_call("tc_1", 3.0))
    execution = n8n_execution(
        "9951", started_at=CALL_START + timedelta(seconds=3.1), call_id=call.external_id
    )
    listing, detail = _n8n_answers([execution])

    _open_calls_screen(client, auth_cookies, db, agent, listing, detail)
    assert listing.await_count == 0

    summary, _l, _d = _refresh(client, auth_cookies, call, [execution])
    assert summary["matched"] == 1


@pytest.mark.usefixtures("_calls_are_recent")
def test_nothing_found_is_not_final_while_the_call_has_only_just_ended(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    assert (
        _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies)).status_code
        == 200
    )
    call = _store_call(db, agent, _price_call("tc_1", 3.0))
    call.ended_at = datetime.now(UTC).replace(tzinfo=None)  # hung up a moment ago
    db.add(call)
    db.commit()
    execution = n8n_execution(
        "9971", started_at=CALL_START + timedelta(seconds=3.1), call_id=call.external_id
    )
    nothing_yet, _ = _n8n_answers([])
    listing, detail = _n8n_answers([execution])

    # The workflow is still running: n8n has nothing saved yet.
    _open_calls_screen(client, auth_cookies, db, agent, nothing_yet, detail)
    assert nothing_yet.await_count == 1
    db.refresh(call)
    assert call.executions_checked_at is None

    # Asked again on the next sync, and found.
    _open_calls_screen(client, auth_cookies, db, agent, listing, detail)
    assert len(_trace(client, auth_cookies, call)["executions"]) == 1
    db.refresh(call)
    assert call.executions_checked_at is not None


@pytest.mark.usefixtures("_calls_are_recent")
def test_a_call_with_a_problem_of_its_own_does_not_hold_up_the_others(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    assert (
        _map(client, auth_cookies, agent.id, _n8n(client, auth_cookies)).status_code
        == 200
    )
    older = _store_call(db, agent, _price_call("tc_1", 3.0))
    newer = _store_call(db, agent, _price_call("tc_1", 3.0))
    newer.started_at = older.started_at + timedelta(hours=1)
    newer.ended_at = newer.started_at + timedelta(minutes=1)
    db.add(newer)
    db.commit()
    good = n8n_execution(
        "9981",
        started_at=CALL_START + timedelta(seconds=3.1),
        call_id=older.external_id,
    )
    listing, detail = _n8n_answers([good])
    answers = listing.return_value

    def answer(*_args: Any, **kwargs: Any) -> Any:
        # The newer call is looked up first, and its lookup fails.
        if kwargs["started_after"] > CALL_START + timedelta(minutes=30):
            raise N8nError("n8n answered 500")
        return answers

    listing.side_effect = answer
    _open_calls_screen(client, auth_cookies, db, agent, listing, detail)
    assert listing.await_count == 2
    assert len(_trace(client, auth_cookies, older)["executions"]) == 1
    db.refresh(newer)
    assert newer.executions_checked_at is None
