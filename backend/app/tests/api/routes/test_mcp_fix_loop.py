"""The fix loop through MCP (10.16): get_issue answers every detail about an issue,
and list_calls with the issue answers its calls with its findings in each. Calls are
invented."""

from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.tests.api.routes.test_mcp_issues import (
    API,
    FULL,
    _agent,
    _booking,
    _call,
    _headers,
    _issues,
    _person,
    _settings,  # noqa: F401 - the autouse fixture that sets up MCP sign-in
)

MISSING_ZIP = {**FULL, "postalCode": ""}


def _issue(client: TestClient, user: Any, issue_id: str) -> Any:
    return client.get(
        f"{API}/mcp/workspaces/{user.company_id}/issues/{issue_id}",
        headers=_headers(user),
    )


def _calls(client: TestClient, user: Any, **params: Any) -> Any:
    return client.get(
        f"{API}/mcp/workspaces/{user.company_id}/calls",
        headers=_headers(user),
        params=params,
    )


def _missing_details_issue(client: TestClient, user: Any) -> dict[str, Any]:
    body = _issues(client, user).json()
    (issue,) = (
        i
        for i in body["data"]["issues"]
        if i["check_type"] == "booking_details_missing"
    )
    return issue


def test_get_issue_answers_the_check_setting_versions_and_totals(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, MISSING_ZIP), version=14)
    _call(db, agent, _booking(1, MISSING_ZIP), version=15)
    _call(db, agent, _booking(1, MISSING_ZIP), version=15)
    _call(db, agent, _booking(1, FULL), version=16, days_ago=0.5)
    issue_id = _missing_details_issue(client, user)["id"]

    response = _issue(client, user, issue_id)

    assert response.status_code == 200
    data = response.json()["data"]
    check = data["check"]
    assert (check["type"], check["kind"], check["version"]) == (
        "booking_details_missing",
        "code_based",
        1,
    )
    assert check["description"]
    assert (check["provider"], check["model"]) == (None, None)
    assert set(check["detail_fields"]) == {"empty"}
    assert check["needs"]
    assert data["setting"] == {"mode": "fails", "default": "fails", "since": None}
    assert data["versions"] == [
        {"version": "15", "calls": 2},
        {"version": "14", "calls": 1},
    ]
    assert data["live_version"] == "16"
    assert (data["findings_all_time"], data["calls_all_time"]) == (3, 3)
    steps = " ".join(response.json()["next_steps"])
    assert "list_calls" in steps and "limit" in steps


def test_list_calls_with_the_issue_answers_its_findings_on_each_call(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Invented")
    for version in (14, 15, 15):
        _call(db, agent, _booking(1, MISSING_ZIP), version=version)
    issue_id = _missing_details_issue(client, user)["id"]

    body = _calls(client, user, issue_id=issue_id, limit=2).json()

    calls = body["data"]["calls"]
    assert len(calls) == 2
    assert body["next_cursor"]
    for call in calls:
        assert call["agent_version"] in {"14", "15"}
        (finding,) = call["issue_findings"]
        assert finding["effect"] == "fails"
        assert finding["check_version"] == 1
        assert finding["event_ids"]
        assert "postalCode" in finding["detail"]["empty"]
        # Names of the empty arguments only, never a value from the call.
        assert FULL["full_name"] not in str(finding)
    assert any("get_issue" in rule for rule in body["rules"])


def test_list_calls_without_an_issue_is_unchanged(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, MISSING_ZIP))

    (call,) = _calls(client, user).json()["data"]["calls"]

    assert call["issue_findings"] is None
    assert call["agent_version"] is None


def test_the_issue_fix_task_names_list_calls_and_mark_issue_fixed(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, MISSING_ZIP))
    issue_id = _missing_details_issue(client, user)["id"]

    from app.api.routes.mcp import _task_steps  # noqa: PLC0415
    from app.models.enums import TaskKind  # noqa: PLC0415

    class _Task:
        kind = TaskKind.ISSUE_FIX
        ref = issue_id
        agent_id = agent.id

    steps = " ".join(_task_steps(_Task()))  # type: ignore[arg-type]
    assert "list_calls" in steps
    assert "mark_issue_fixed" in steps
    assert "the person resolves" not in steps
