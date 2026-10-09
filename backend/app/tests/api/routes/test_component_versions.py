"""Which version served a call. Every Retell and n8n payload here is invented."""

import copy
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
from app.models import Agent, Call, ComponentVersion
from app.models.enums import Platform
from app.services import component_versions
from app.services.mappings.retell import retell_call_to_trace
from app.services.n8n import N8nConnectionResult, N8nExecutionSummary, N8nWorkflow
from app.services.retell import RetellCall
from app.services.retell_versions import RetellReadError
from app.tests.utils.n8n_payloads import n8n_execution
from app.tests.utils.retell_payloads import START_MS, invocation, result, retell_call
from app.tests.utils.utils import extract_cookies, random_email, random_lower_string

pytestmark = pytest.mark.provider_versions

API = settings.API_V1_STR
CALL_START = datetime.fromtimestamp(START_MS / 1000, tz=UTC)
SERVICE = "app.services.component_versions"


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    yield
    encryption._fernet.cache_clear()


def _agent_settings(version: int, **changes: Any) -> dict[str, Any]:
    settings_: dict[str, Any] = {
        "agent_id": "agent_invented_1",
        "agent_name": "Invented Agent",
        "version": version,
        "is_published": True,
        "last_modification_timestamp": 1_750_000_000_000 + version,
        "voice_id": "voice_invented",
        "language": "en-US",
        "webhook_url": "https://example.com/hook",
        "response_engine": {
            "type": "retell-llm",
            "llm_id": "llm_invented_1",
            "version": version,
        },
    }
    settings_.update(changes)
    return settings_


def _llm(version: int, prompt: str = "You are an invented agent.", **changes: Any):
    llm: dict[str, Any] = {
        "llm_id": "llm_invented_1",
        "version": version,
        "is_published": True,
        "last_modification_timestamp": 1_750_000_000_000 + version,
        "general_prompt": prompt,
        "begin_message": "Hello",
        "model": "gpt-invented",
        "model_temperature": 0.2,
        "general_tools": [
            {
                "type": "custom",
                "name": "get_price",
                "url": "https://n8n.example.com/webhook/invented",
                "headers": {"Authorization": "Bearer invented-secret"},
            },
            {"type": "end_call", "name": "end_call"},
        ],
    }
    llm.update(changes)
    return llm


class Retell:
    """Stand-in for Retell's version reads, counting how often each is asked."""

    def __init__(self) -> None:
        self.agents: dict[str, dict[str, Any]] = {}
        self.llms: dict[str, dict[str, Any]] = {}
        self.flows: dict[str, dict[str, Any]] = {}
        self.agent_reads = AsyncMock(side_effect=self._agent)
        self.llm_reads = AsyncMock(side_effect=self._llm)
        self.flow_reads = AsyncMock(side_effect=self._flow)

    def version(self, number: int, **llm_changes: Any) -> None:
        self.agents[str(number)] = _agent_settings(number)
        self.llms[str(number)] = _llm(number, **llm_changes)

    async def _agent(self, _key: str, _agent_id: str, version: Any) -> dict[str, Any]:
        if str(version) not in self.agents:
            raise RetellReadError("Retell answered 404")
        return copy.deepcopy(self.agents[str(version)])

    async def _llm(self, _key: str, _llm_id: str, version: Any) -> dict[str, Any]:
        return copy.deepcopy(self.llms[str(version)])

    async def _flow(self, _key: str, _flow_id: str, version: Any) -> dict[str, Any]:
        return copy.deepcopy(self.flows[str(version)])

    def patched(self) -> Any:
        return (
            patch(f"{SERVICE}.get_retell_agent_at_version", self.agent_reads),
            patch(f"{SERVICE}.get_retell_llm_at_version", self.llm_reads),
            patch(
                f"{SERVICE}.get_retell_conversation_flow_at_version", self.flow_reads
            ),
        )


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
    agent = db.get(Agent, uuid.UUID(r.json()["id"]))
    assert agent is not None
    agent.platform = Platform.RETELL
    agent.platform_agent_id = "agent_invented_1"
    agent.integration_id = uuid.UUID(retell_id)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _pull(
    client: TestClient,
    cookies: dict[str, str],
    agent: Agent,
    retell: Retell,
    versions: list[int],
    timeline: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Pull one new call per agent version. Returns the calls' Connexity ids."""
    calls = []
    for offset, version in enumerate(versions):
        call_id = f"call_{uuid.uuid4().hex[:10]}"
        start = START_MS + offset * 1000 + int(uuid.uuid4().int % 1_000_000) * 1000
        calls.append(
            RetellCall(
                call_id=call_id,
                start_timestamp=start,
                raw=retell_call(
                    call_id,
                    agent_id="agent_invented_1",
                    start_ms=start,
                    agent_version=version,
                    timeline=timeline,
                ),
            )
        )
    agent_patch, llm_patch, flow_patch = retell.patched()
    with (
        agent_patch,
        llm_patch,
        flow_patch,
        patch(
            "app.services.call_sync.list_retell_calls", AsyncMock(return_value=calls)
        ),
    ):
        r = client.post(f"{API}/agents/{agent.id}/calls/refresh", cookies=cookies)
    assert r.status_code == 200, r.text
    listed = client.get(
        f"{API}/agents/{agent.id}/calls", params={"limit": 200}, cookies=cookies
    ).json()["data"]
    by_external = {item["external_id"]: item["id"] for item in listed}
    return [by_external[call.call_id] for call in calls]


def _served_by(client: TestClient, cookies: dict[str, str], call_id: str) -> dict:
    r = client.get(f"{API}/calls/{call_id}/trace", cookies=cookies)
    assert r.status_code == 200, r.text
    return {item["kind"]: item for item in r.json()["served_by"]}


def _call(client: TestClient, cookies: dict[str, str], call_id: str) -> dict:
    r = client.get(f"{API}/calls/{call_id}", cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json()


def _other_company(client: TestClient) -> dict[str, str]:
    email, password = random_email(), random_lower_string()
    client.post(f"{API}/users/signup", json={"email": email, "password": password})
    login = client.post(
        f"{API}/login/access-token", data={"username": email, "password": password}
    )
    return extract_cookies(login)


def test_a_call_on_a_new_version_records_agent_prompt_and_model_once(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    retell = Retell()
    retell.version(7)

    first, second = _pull(client, auth_cookies, agent, retell, [7, 7])

    # Two calls on one version: Retell is read once.
    assert retell.agent_reads.await_count == 1
    assert retell.llm_reads.await_count == 1

    served = _served_by(client, auth_cookies, first)
    assert set(served) == {"agent", "prompt", "model"}
    assert (served["agent"]["name"], served["agent"]["version"]) == (
        "Invented Agent",
        "7",
    )
    assert (served["prompt"]["ref"], served["prompt"]["version"]) == (
        "llm_invented_1",
        "7",
    )
    assert (served["model"]["name"], served["model"]["version"]) == (
        "gpt-invented",
        None,
    )
    for item in served.values():
        assert len(item["fingerprint"]) == 64
        assert item["component_version_id"]

    call = _call(client, auth_cookies, first)
    assert call["agent_version"] == "7"
    assert len(call["state_fingerprint"]) == 64
    assert (
        _call(client, auth_cookies, second)["state_fingerprint"]
        == call["state_fingerprint"]
    )


def test_fingerprints_follow_content_not_version_numbers(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    retell = Retell()
    retell.version(1)
    retell.version(2)  # republished with nothing changed
    retell.version(3, general_prompt="You are a different invented agent.")
    retell.version(4, model="gpt-invented-next")

    one, two, three, four = (
        (
            _served_by(client, auth_cookies, call_id),
            _call(client, auth_cookies, call_id),
        )
        for call_id in _pull(client, auth_cookies, agent, retell, [1, 2, 3, 4])
    )

    def prints(pair: Any) -> tuple[str, str, str, str]:
        served, call = pair
        return (
            served["agent"]["fingerprint"],
            served["prompt"]["fingerprint"],
            served["model"]["fingerprint"],
            call["state_fingerprint"],
        )

    # Same content under a new version number: nothing differs.
    assert prints(one) == prints(two)
    # A new prompt: the prompt and the call's state differ; agent and model do not.
    assert prints(three)[0] == prints(one)[0]
    assert prints(three)[1] != prints(one)[1]
    assert prints(three)[2] == prints(one)[2]
    assert prints(three)[3] != prints(one)[3]
    # A new model: only the model and the call's state differ.
    assert prints(four)[:2] == prints(one)[:2]
    assert prints(four)[2] != prints(one)[2]
    assert prints(four)[3] != prints(one)[3]


def test_stored_content_has_no_credentials_and_can_be_read_by_its_company_only(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    retell = Retell()
    retell.version(5)
    (call_id,) = _pull(client, auth_cookies, agent, retell, [5])
    prompt = _served_by(client, auth_cookies, call_id)["prompt"]

    listed = client.get(
        f"{API}/agents/{agent.id}/component-versions", cookies=auth_cookies
    )
    assert listed.status_code == 200
    assert {item["kind"] for item in listed.json()} == {"agent", "prompt", "model"}
    assert "content" not in listed.json()[0]
    only_prompts = client.get(
        f"{API}/agents/{agent.id}/component-versions",
        params={"kind": "prompt"},
        cookies=auth_cookies,
    ).json()
    assert [item["kind"] for item in only_prompts] == ["prompt"]

    path = (
        f"{API}/agents/{agent.id}/component-versions/{prompt['component_version_id']}"
    )
    r = client.get(path, cookies=auth_cookies)
    assert r.status_code == 200, r.text
    content = r.json()["content"]
    assert content["general_prompt"] == "You are an invented agent."
    assert (
        content["general_tools"][0]["url"] == "https://n8n.example.com/webhook/invented"
    )
    assert content["general_tools"][0]["headers"] == {"Authorization": "•••"}
    assert "invented-secret" not in r.text
    # The model is its own component, and volatile fields are not content.
    assert "model" not in content and "version" not in content

    rows = db.exec(
        select(ComponentVersion).where(ComponentVersion.agent_id == agent.id)
    ).all()
    assert "invented-secret" not in str([row.content for row in rows])

    other = _other_company(client)
    assert client.get(path, cookies=other).status_code == 404
    assert (
        client.get(
            f"{API}/agents/{agent.id}/component-versions", cookies=other
        ).status_code
        == 404
    )
    assert client.get(path).status_code == 401
    wrong_agent = _agent(client, auth_cookies, db)
    assert (
        client.get(
            f"{API}/agents/{wrong_agent.id}/component-versions/"
            f"{prompt['component_version_id']}",
            cookies=auth_cookies,
        ).status_code
        == 404
    )


def test_a_conversation_flow_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    retell = Retell()
    retell.agents["9"] = _agent_settings(
        9,
        response_engine={
            "type": "conversation-flow",
            "conversation_flow_id": "flow_invented_1",
            "version": 4,
        },
    )
    retell.flows["4"] = {
        "conversation_flow_id": "flow_invented_1",
        "version": 4,
        "global_prompt": "Invented flow",
        "nodes": [{"id": "n1", "type": "conversation"}],
        "model_choice": {"type": "cascading", "model": "gpt-invented-flow"},
    }
    (call_id,) = _pull(client, auth_cookies, agent, retell, [9])
    served = _served_by(client, auth_cookies, call_id)
    assert set(served) == {"agent", "flow", "model"}
    assert (served["flow"]["ref"], served["flow"]["version"]) == (
        "flow_invented_1",
        "4",
    )
    assert served["model"]["name"] == "gpt-invented-flow"
    assert retell.llm_reads.await_count == 0


@pytest.mark.parametrize(
    "failure",
    [
        RetellReadError("Could not reach Retell"),
        RetellReadError("Retell did not answer with JSON"),
        RuntimeError("anything at all"),
    ],
)
def test_an_unreadable_retell_does_not_stop_the_call_and_the_backfill_resolves_it(
    client: TestClient, auth_cookies: dict[str, str], db: Session, failure: Exception
) -> None:
    agent = _agent(client, auth_cookies, db)
    down = Retell()
    down.agent_reads.side_effect = failure
    first, second = _pull(client, auth_cookies, agent, down, [11, 11])

    served = _served_by(client, auth_cookies, first)
    assert set(served) == {"agent"}
    assert served["agent"]["version"] == "11"
    assert served["agent"]["fingerprint"] is None
    call = _call(client, auth_cookies, first)
    assert (call["agent_version"], call["state_fingerprint"]) == ("11", None)

    retell = Retell()
    retell.version(11)
    agent_patch, llm_patch, flow_patch = retell.patched()
    with agent_patch, llm_patch, flow_patch:
        resolved = client.post(
            f"{API}/agents/{agent.id}/versions/resolve", cookies=auth_cookies
        )
        again = client.post(
            f"{API}/agents/{agent.id}/versions/resolve", cookies=auth_cookies
        )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json() == {
        "calls_resolved": 2,
        "calls_unresolved": 0,
        "versions_read": 1,
        "skills_recorded": 0,
        "problems": [],
    }
    # Two calls, one version: read once. Running it again does nothing.
    assert retell.agent_reads.await_count == 1
    assert again.json()["calls_resolved"] == 0
    assert again.json()["versions_read"] == 0

    assert set(_served_by(client, auth_cookies, second)) == {"agent", "prompt", "model"}
    assert len(_call(client, auth_cookies, second)["state_fingerprint"]) == 64
    rows = db.exec(
        select(ComponentVersion).where(ComponentVersion.agent_id == agent.id)
    ).all()
    assert sorted(row.kind for row in rows) == ["agent", "model", "prompt"]


def test_the_backfill_reports_a_version_it_cannot_read(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    down = Retell()
    down.agent_reads.side_effect = RetellReadError("Could not reach Retell")
    _pull(client, auth_cookies, agent, down, [20, 21])

    retell = Retell()
    retell.version(20)  # version 21 no longer exists at Retell
    agent_patch, llm_patch, flow_patch = retell.patched()
    with agent_patch, llm_patch, flow_patch:
        r = client.post(
            f"{API}/agents/{agent.id}/versions/resolve", cookies=auth_cookies
        )
    body = r.json()
    assert (body["calls_resolved"], body["calls_unresolved"]) == (1, 1)
    assert body["problems"] == ["version 21: Retell answered 404"]
    assert (
        client.post(
            f"{API}/agents/{agent.id}/versions/resolve", cookies=_other_company(client)
        ).status_code
        == 404
    )


# ── Skills ─────────────────────────────────────────────────────────


def _map_tool(client: TestClient, cookies: dict[str, str], agent: Agent) -> None:
    ok = AsyncMock(
        return_value=N8nConnectionResult(ok=True, base_url="https://n8n.example.com")
    )
    with patch("app.api.routes.integrations.check_n8n_connection", ok):
        integration_id = client.post(
            f"{API}/integrations/",
            json={
                "provider": "n8n",
                "name": f"n8n-{uuid.uuid4().hex[:6]}",
                "api_key": "n8n_api_invented_key",
                "base_url": "https://n8n.example.com",
            },
            cookies=cookies,
        ).json()["id"]
    with patch(
        "app.api.routes.tool_backends.get_n8n_workflow",
        AsyncMock(return_value=N8nWorkflow(id="wf_invented_1", name="Invented lookup")),
    ):
        r = client.put(
            f"{API}/agents/{agent.id}/tool-backends",
            json={
                "tool_name": "get_price",
                "integration_id": integration_id,
                "workflow_id": "wf_invented_1",
            },
            cookies=cookies,
        )
    assert r.status_code == 200, r.text


def _stored_call(db: Session, agent: Agent) -> Call:
    payload = retell_call(
        f"call_{uuid.uuid4().hex[:10]}",
        agent_id="agent_invented_1",
        timeline=[
            invocation("tc_1", "get_price", '{"sku": "A-1"}', time_sec=3.0),
            result("tc_1", '{"price": 120}', successful=True, time_sec=4.0),
        ],
    )
    return crud.store_trace(
        session=db,
        trace=retell_call_to_trace(payload),
        agent_id=agent.id,
        company_id=agent.company_id,
        raw=payload,
    ).call


def _find_executions(
    client: TestClient, cookies: dict[str, str], call: Call, execution: dict[str, Any]
) -> None:
    listing = AsyncMock(
        return_value=[
            N8nExecutionSummary(
                id=str(execution["id"]),
                workflow_id=execution["workflowId"],
                started_at=CALL_START + timedelta(seconds=3.1),
            )
        ]
    )
    with (
        patch("app.services.executions.list_n8n_executions", listing),
        patch(
            "app.services.executions.get_n8n_execution",
            AsyncMock(return_value=execution),
        ),
    ):
        r = client.post(f"{API}/calls/{call.id}/executions/refresh", cookies=cookies)
    assert r.status_code == 200 and r.json()["matched"] == 1, r.text


def _execution(call: Call, execution_id: str, *, version: str, code: str) -> dict:
    payload = n8n_execution(
        execution_id,
        started_at=CALL_START + timedelta(seconds=3.1),
        call_id=call.external_id,
    )
    payload["workflowVersionId"] = version
    nodes = payload["workflowData"]["nodes"]
    nodes[1]["parameters"] = {
        "jsCode": code,
        "headerParameters": {
            "parameters": [{"name": "X-Key", "value": "invented-secret"}]
        },
    }
    nodes[1]["position"] = [int(execution_id), 0]
    return payload


def test_a_workflow_that_ran_is_recorded_as_a_skill_version(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    _map_tool(client, auth_cookies, agent)
    first, second, third = (_stored_call(db, agent) for _ in range(3))

    _find_executions(
        client,
        auth_cookies,
        first,
        _execution(first, "1", version="v-a", code="return 1"),
    )
    # The same workflow content, with a node moved on the canvas: the same version.
    _find_executions(
        client,
        auth_cookies,
        second,
        _execution(second, "2", version="v-a", code="return 1"),
    )
    _find_executions(
        client,
        auth_cookies,
        third,
        _execution(third, "3", version="v-b", code="return 2"),
    )

    skills = client.get(
        f"{API}/agents/{agent.id}/component-versions",
        params={"kind": "skill"},
        cookies=auth_cookies,
    ).json()
    assert sorted(item["version"] for item in skills) == ["v-a", "v-b"]
    assert len({item["fingerprint"] for item in skills}) == 2

    one = _served_by(client, auth_cookies, str(first.id))["skill"]
    two = _served_by(client, auth_cookies, str(second.id))["skill"]
    three = _served_by(client, auth_cookies, str(third.id))["skill"]
    assert (one["name"], one["ref"], one["version"]) == (
        "Invented price lookup",
        "wf_invented_1",
        "v-a",
    )
    assert one["fingerprint"] == two["fingerprint"] != three["fingerprint"]

    content = client.get(
        f"{API}/agents/{agent.id}/component-versions/{three['component_version_id']}",
        cookies=auth_cookies,
    )
    assert "return 2" in content.text
    assert "invented-secret" not in content.text
    assert "position" not in content.text

    # A skill is not part of the call's own fingerprint.
    assert _call(client, auth_cookies, str(first.id))["state_fingerprint"] is None


def test_the_backfill_records_the_skill_of_an_execution_stored_earlier(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    _map_tool(client, auth_cookies, agent)
    call = _stored_call(db, agent)
    execution = _execution(call, "7", version="v-old", code="return 7")
    with patch(
        "app.services.executions.record_skill_version", return_value=None
    ) as not_recorded:
        _find_executions(client, auth_cookies, call, execution)
    assert not_recorded.called
    assert "fingerprint" in _served_by(client, auth_cookies, str(call.id))["skill"]
    assert (
        _served_by(client, auth_cookies, str(call.id))["skill"]["fingerprint"] is None
    )

    reads = AsyncMock(return_value=execution)
    with patch(f"{SERVICE}.get_n8n_execution", reads):
        first = client.post(
            f"{API}/agents/{agent.id}/versions/resolve", cookies=auth_cookies
        ).json()
        second = client.post(
            f"{API}/agents/{agent.id}/versions/resolve", cookies=auth_cookies
        ).json()
    assert (first["skills_recorded"], second["skills_recorded"]) == (1, 0)
    assert reads.await_count == 1
    skill = _served_by(client, auth_cookies, str(call.id))["skill"]
    assert len(skill["fingerprint"]) == 64


def test_a_workflow_with_no_version_id_is_filed_under_its_content(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    _map_tool(client, auth_cookies, agent)
    first, second = _stored_call(db, agent), _stored_call(db, agent)
    one = _execution(first, "1", version="unused", code="return 1")
    two = _execution(second, "2", version="unused", code="return 2")
    del one["workflowVersionId"], two["workflowVersionId"]

    _find_executions(client, auth_cookies, first, one)
    _find_executions(client, auth_cookies, second, two)

    a = _served_by(client, auth_cookies, str(first.id))["skill"]
    b = _served_by(client, auth_cookies, str(second.id))["skill"]
    # Each is found, under its own version, and they differ.
    assert a["component_version_id"] and b["component_version_id"]
    assert a["version"] == a["fingerprint"][:12]
    assert a["fingerprint"] != b["fingerprint"]
    with patch(f"{SERVICE}.get_n8n_execution", AsyncMock()) as reads:
        r = client.post(
            f"{API}/agents/{agent.id}/versions/resolve", cookies=auth_cookies
        )
    assert r.json()["skills_recorded"] == 0
    assert reads.await_count == 0


def test_a_prompt_with_no_version_is_filed_under_its_content(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    retell = Retell()
    engine = {"type": "retell-llm", "llm_id": "llm_invented_1"}
    retell.agents["30"] = _agent_settings(30, response_engine=engine)
    retell.llms["None"] = _llm(1, prompt="First prompt")
    (first,) = _pull(client, auth_cookies, agent, retell, [30])
    retell.agents["31"] = _agent_settings(31, response_engine=engine)
    retell.llms["None"] = _llm(1, prompt="Second prompt")
    (second,) = _pull(client, auth_cookies, agent, retell, [31])

    one = _served_by(client, auth_cookies, first)["prompt"]
    two = _served_by(client, auth_cookies, second)["prompt"]
    assert one["fingerprint"] != two["fingerprint"]
    assert one["component_version_id"] != two["component_version_id"]


def test_stored_calls_are_resolved_in_the_background_without_being_asked(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _agent(client, auth_cookies, db)
    down = Retell()
    down.agent_reads.side_effect = RetellReadError("Could not reach Retell")
    (call_id,) = _pull(client, auth_cookies, agent, down, [40])
    assert _call(client, auth_cookies, call_id)["state_fingerprint"] is None
    reads_at_arrival = down.agent_reads.await_count

    def open_calls_screen(retell: Retell) -> None:
        db.refresh(agent)
        agent.calls_last_synced_at = None  # the list is stale: a sync is due
        db.add(agent)
        db.commit()
        agent_patch, llm_patch, flow_patch = retell.patched()
        with (
            agent_patch,
            llm_patch,
            flow_patch,
            patch(
                "app.services.call_sync.list_retell_calls", AsyncMock(return_value=[])
            ),
        ):
            r = client.get(f"{API}/agents/{agent.id}/calls", cookies=auth_cookies)
        assert r.status_code == 200, r.text

    # Retell still down: the pass tries, fails, and the next one waits.
    component_versions._retry_not_before.clear()
    open_calls_screen(down)
    assert down.agent_reads.await_count == reads_at_arrival + 1
    retell = Retell()
    retell.version(40)
    open_calls_screen(retell)
    assert retell.agent_reads.await_count == 0
    assert _call(client, auth_cookies, call_id)["state_fingerprint"] is None

    # Once the wait is over, opening the screen resolves the call.
    component_versions._retry_not_before.clear()
    open_calls_screen(retell)
    assert retell.agent_reads.await_count == 1
    assert len(_call(client, auth_cookies, call_id)["state_fingerprint"]) == 64
    assert set(_served_by(client, auth_cookies, call_id)) == {
        "agent",
        "prompt",
        "model",
    }

    # Nothing left to do: Retell is not read again.
    open_calls_screen(retell)
    assert retell.agent_reads.await_count == 1
