"""The agent page's version filter: the Overview, the calls, the issues, the spec and
the tests of one agent version, on invented calls (plan
`plans/2026-11-19-agent-versions.md`)."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.tests.api.routes.test_call_screen import _signed_in
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _headers,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_spec_api import API, RULES, _write

EMPTY_ZIP = {**FULL, "postalCode": ""}


def test_the_overview_and_calls_of_one_version(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    # Two calls on 87, one of them a booking without a zip; then one on 88, live.
    _call(db, agent, _booking(1, EMPTY_ZIP), days_ago=3, version=87)
    _call(db, agent, _booking(2, FULL), days_ago=2, version=87)
    _call(db, agent, _booking(3, FULL), days_ago=1, version=88)

    page = client.get(f"{API}/agents/{agent.id}/page", cookies=cookies).json()
    assert page["calls"] == 3
    assert page["version"] is None
    assert page["versions"] == [
        {"version": "88", "calls": 1, "live": True},
        {"version": "87", "calls": 2, "live": False},
    ]

    on_87 = client.get(
        f"{API}/agents/{agent.id}/page", params={"version": "87"}, cookies=cookies
    ).json()
    assert on_87["calls"] == 2
    assert on_87["version"] == "87"
    assert len(on_87["version_days"]) == 2
    # The live version is still named, whatever is picked.
    assert on_87["live_version"] == "88"

    calls = client.get(
        f"{API}/calls",
        params={"agent_id": str(agent.id), "version": "87"},
        cookies=cookies,
    ).json()
    assert [c["agent_version"] for c in calls["data"]] == ["87", "87"]
    assert calls["tiles"]["calls"] == 2

    # The assistant reads the same, and the issues found on 87's calls only.
    base = f"{API}/mcp/workspaces/{user.company_id}"
    agent_answer = client.get(
        f"{base}/agents/{agent.id}", params={"version": "87"}, headers=_headers(user)
    ).json()
    assert agent_answer["data"]["calls"] == 2
    assert agent_answer["data"]["version"] == "87"
    overall = client.get(f"{base}/agents/{agent.id}", headers=_headers(user)).json()
    assert any("compare versions" in s for s in overall["next_steps"])
    mcp_calls = client.get(
        f"{base}/calls",
        params={"agent_id": str(agent.id), "version": "88"},
        headers=_headers(user),
    ).json()
    assert [c["agent_version"] for c in mcp_calls["data"]["calls"]] == ["88"]
    issues_87 = client.get(
        f"{base}/issues",
        params={"agent_id": str(agent.id), "version": "87"},
        headers=_headers(user),
    ).json()["data"]
    issues_88 = client.get(
        f"{base}/issues",
        params={"agent_id": str(agent.id), "version": "88"},
        headers=_headers(user),
    ).json()["data"]
    assert [i["calls_affected"] for i in issues_87["issues"]] == [1]
    assert issues_87["issues"][0]["calls_total"] == 2
    assert issues_88["issues"] == []


def test_the_spec_in_force_for_a_version(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    _call(db, agent, _booking(1, FULL), days_ago=2, version=87)
    _write(client, user, agent, [RULES[0]])  # spec 1, written for 87
    _call(db, agent, _booking(2, FULL), days_ago=1, version=88)
    # Version 88's first call adopts a copy of spec 1 for it; then a new spec for 88.
    _write(client, user, agent, [RULES[0], RULES[1]])

    def spec(**params: str) -> dict[str, object]:
        return client.get(
            f"{API}/agents/{agent.id}/spec", params=params, cookies=cookies
        ).json()

    latest = spec()["spec"]
    assert (latest["version"], latest["agent_version"]) == (3, "88")
    for_87 = spec(for_version="87")
    assert for_87["spec"]["version"] == 1
    assert for_87["spec"]["agent_version"] == "87"
    assert for_87["for_version"] == "87"
    # A later version with no spec of its own keeps the one in force.
    assert spec(for_version="90")["spec"]["version"] == 3
    # A version before any spec has none.
    before = spec(for_version="80")
    assert before["spec"] is None and before["groups"] == []
    assert before["for_version"] == "80"

    tests = client.get(
        f"{API}/agents/{agent.id}/tests", params={"version": "87"}, cookies=cookies
    ).json()
    assert tests["results"]["version"] == "87"
    assert tests["results"]["verdict"] == "not_verified"
