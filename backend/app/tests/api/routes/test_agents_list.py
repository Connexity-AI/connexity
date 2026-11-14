"""The Agents page (`GET /agents/list`) and `list_agents`' type and calls, on invented
calls (plan `plans/2026-11-14-agents-page.md`)."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import Agent
from app.models.call_pull import CallPullAccount
from app.models.integration import Integration
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_issues_list import _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _headers,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_spec_api import _catalogue

API = settings.API_V1_STR


def _flow(db: Session, agent: Agent, version: str) -> None:
    """Record ``version`` of the agent as served by a conversational flow."""
    crud.record_component_version(
        session=db,
        agent_id=agent.id,
        company_id=agent.company_id,
        kind="flow",
        name="Flow",
        ref="flow_invented",
        version=version,
        fingerprint=uuid.uuid4().hex,
        content={"nodes": [{"instruction": "Greet the caller"}]},
    )
    crud.record_component_version(
        session=db,
        agent_id=agent.id,
        company_id=agent.company_id,
        kind="agent",
        name=agent.name,
        ref=agent.platform_agent_id or "",
        version=version,
        fingerprint=uuid.uuid4().hex,
        content={},
        links=[{"kind": "flow", "ref": "flow_invented", "version": version}],
    )
    db.commit()


def test_the_page_lists_linked_agents_with_type_and_calls(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    busy = _agent(db, user, "Busy desk")
    _catalogue(db, busy, "7")
    for days in (1, 2, 40):
        _call(db, busy, _booking(1, FULL), days_ago=days, version=7)
    flow = _agent(db, user, "Flow line")
    _flow(db, flow, "3")
    _call(db, flow, _booking(1, FULL), days_ago=1, version=3)
    # Not read yet: no type.
    unknown = _agent(db, user, "Another line")
    _call(db, unknown, _booking(1, FULL), days_ago=1, version=5)
    _agent(db, user, "A quiet line")
    # Made by hand in 1.x, not linked to Retell: not on the page.
    db.add(Agent(name="Old draft", company_id=user.company_id))
    db.commit()

    r = client.get(f"{API}/agents/list", cookies=cookies)

    assert r.status_code == 200, r.text
    body = r.json()
    rows = [(a["name"], a["type"], a["calls"], a["spec"]) for a in body["data"]]
    # Most calls first, then by name.
    assert rows == [
        ("Busy desk", "single_prompt", 2, "none"),
        ("Another line", None, 1, "none"),
        ("Flow line", "conversational_flow", 1, "none"),
        ("A quiet line", None, 0, "none"),
    ]
    assert body["data"][0]["platform"] == "retell"
    assert body["period"] == "30d"
    assert body["synced_at"] is None
    longer = client.get(
        f"{API}/agents/list", cookies=cookies, params={"period": "90d"}
    ).json()
    assert longer["data"][0]["calls"] == 3


def test_synced_is_the_latest_pull_of_the_workspaces_retell_accounts(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    integration = db.get(Integration, agent.integration_id)
    assert integration is not None and integration.key_fingerprint
    pulled = datetime.now(UTC) - timedelta(minutes=5)
    db.add(
        CallPullAccount(
            key_fingerprint=integration.key_fingerprint,
            cursor=pulled,
            last_pulled_at=pulled,
        )
    )
    # Another workspace's account does not count.
    db.add(
        CallPullAccount(
            key_fingerprint=uuid.uuid4().hex,
            cursor=datetime.now(UTC),
            last_pulled_at=datetime.now(UTC),
        )
    )
    db.commit()

    body = client.get(f"{API}/agents/list", cookies=cookies).json()

    assert datetime.fromisoformat(body["synced_at"]) == pulled


def test_a_spec_shows_on_the_list(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, "7")
    _call(db, agent, _booking(1, FULL), days_ago=1, version=7)
    written = client.post(
        f"{API}/mcp/workspaces/{user.company_id}/agents/{agent.id}/spec",
        headers=_headers(user),
        json={
            "rules": [
                {
                    "text": "Never book outside opening hours",
                    "category": "booking",
                    "quote": "Only book within opening hours",
                }
            ]
        },
    )
    assert written.status_code == 200, written.text

    body = client.get(f"{API}/agents/list", cookies=cookies).json()

    assert body["data"][0]["spec"] == "current"


def test_only_the_open_workspaces_agents(client: TestClient, db: Session) -> None:
    _, cookies = _signed_in(client, db)
    other = _person(db)
    _agent(db, other, "Elsewhere")

    assert client.get(f"{API}/agents/list", cookies=cookies).json()["data"] == []
    assert client.get(f"{API}/agents/list").status_code == 401
    assert (
        client.get(
            f"{API}/agents/list", cookies=cookies, params={"period": "1y"}
        ).status_code
        == 422
    )


def test_list_agents_has_type_and_calls_for_the_period(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, "7")
    _call(db, agent, _booking(1, FULL), days_ago=1, version=7)
    _call(db, agent, _booking(1, FULL), days_ago=20, version=7)
    base = f"{API}/mcp/workspaces/{user.company_id}/agents"

    month = client.get(base, headers=_headers(user)).json()
    week = client.get(base, headers=_headers(user), params={"period": "7d"}).json()

    assert (month["data"][0]["type"], month["data"][0]["calls"]) == ("single_prompt", 2)
    assert week["data"][0]["calls"] == 1
    assert any("calls counts" in rule for rule in month["rules"])
