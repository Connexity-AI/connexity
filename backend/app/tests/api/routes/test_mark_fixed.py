"""Marking an issue fixed through MCP, its version going live, and the issue coming back,
on invented agents and calls (plan `plans/2026-11-17-mark-fixed.md`)."""

from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Agent, User
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    API,
    FULL,
    _agent,
    _booking,
    _call,
    _headers,
    _issues,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)

MISSING_ZIP = FULL | {"postalCode": ""}


def _issue_url(user: User, issue_id: str) -> str:
    return f"{API}/mcp/workspaces/{user.company_id}/issues/{issue_id}"


def _fixed(client: TestClient, user: User, issue_id: str, **body: Any) -> Any:
    return client.post(
        f"{_issue_url(user, issue_id)}/fixed", headers=_headers(user), json=body
    )


def _get(client: TestClient, user: User, issue_id: str) -> Any:
    return client.get(_issue_url(user, issue_id), headers=_headers(user)).json()


def _one_issue(db: Session, client: TestClient) -> tuple[User, Agent, str]:
    user = _person(db)
    agent = _agent(db, user, "Front desk")
    _call(db, agent, _booking(1, MISSING_ZIP), version=15)
    (issue,) = _issues(client, user).json()["data"]["issues"]
    return user, agent, issue["id"]


def test_marked_fixed_waits_for_its_version_then_reopens_on_a_later_call(
    client: TestClient, db: Session
) -> None:
    user, agent, issue_id = _one_issue(db, client)

    r = _fixed(client, user, issue_id, version="16", note="Ask for the zip first")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["state"] == "resolved"
    assert body["data"]["chain"]["fixed"]["version"] == "16"
    assert body["data"]["chain"]["fixed"]["live_at"] is None
    assert "waiting for version 16 to go live" in body["next_steps"][0]
    marked = body["data"]["history"][0]
    assert marked["what"] == "Marked fixed in version 16"
    assert marked["assistant"]
    assert marked["reason"] == "Ask for the zip first"
    # It left the open list.
    assert _issues(client, user).json()["data"]["issues"] == []

    # Calls on the old version, even after the mark, do not reopen it.
    _call(db, agent, _booking(2, MISSING_ZIP), days_ago=0, version=15)
    assert _get(client, user, issue_id)["data"]["state"] == "resolved"

    # A clean call on version 16 makes the fix live.
    _call(db, agent, _booking(3, FULL), days_ago=0, version=16)
    live = _get(client, user, issue_id)
    assert live["data"]["chain"]["fixed"]["live_at"] is not None
    assert live["data"]["history"][0]["kind"] == "live"
    assert live["data"]["history"][0]["what"] == "Version 16 went live"
    assert live["next_steps"][0].endswith("): 1 call, 0 with this issue.")
    assert "and live" in live["next_steps"][1]
    rows = _issues(client, user, status="resolved").json()["data"]["issues"]
    assert rows[0]["fix_live"] is True

    # Found again on version 17: reopened, and the assistant is told.
    _call(db, agent, _booking(4, MISSING_ZIP), days_ago=0, version=17)
    back = _get(client, user, issue_id)
    assert back["data"]["state"] == "reopened"
    assert back["data"]["history"][0]["reason"] == (
        "Came back on version 17, after the fix in version 16 went live"
    )
    assert back["next_steps"][0].endswith("): 2 calls, 1 with this issue.")
    assert "came back after the fix in version 16" in back["next_steps"][1]
    assert "`mark_issue_fixed`" in back["next_steps"][1]

    # Marking it fixed again in a later version works.
    again = _fixed(client, user, issue_id, version="18")
    assert again.status_code == 200, again.text
    assert again.json()["data"]["state"] == "resolved"


def _since(
    client: TestClient, user: User, issue_id: str, version: str | None = None
) -> tuple[dict[str, Any], str]:
    r = client.get(
        _issue_url(user, issue_id),
        headers=_headers(user),
        params={"since_version": version} if version else None,
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["since_version"], r.json()["next_steps"][0]


def test_get_issue_counts_the_calls_since_the_fix_went_live(
    client: TestClient, db: Session
) -> None:
    user, agent, issue_id = _one_issue(db, client)
    # Never marked fixed and no version asked for: nothing to count from.
    assert _get(client, user, issue_id)["data"]["since_version"] is None

    assert _fixed(client, user, issue_id, version="16").status_code == 200
    waiting, step = _since(client, user, issue_id)
    assert waiting == {
        "version": "16",
        "is_fix": True,
        "live_at": None,
        "calls": 0,
        "calls_with_issue": 0,
        "last_call_id": None,
        "last_call_at": None,
    }
    assert "waiting for version 16 to go live" in step

    # Three clean calls on version 16, and one on 15 after it went live, which the
    # old version still served: not counted.
    for n in (2, 3, 4):
        _call(db, agent, _booking(n, FULL), days_ago=0, version=16)
    _call(db, agent, _booking(5, FULL), days_ago=0, version=15)
    clean, step = _since(client, user, issue_id)
    assert (clean["calls"], clean["calls_with_issue"]) == (3, 0)
    assert clean["live_at"] is not None and clean["last_call_id"] is None
    assert step.startswith("Since version 16 went live (")
    assert step.endswith("): 3 calls, 0 with this issue.")
    assert _get(client, user, issue_id)["data"]["state"] == "resolved"

    # A fourth call on version 16 with the issue: reopened, 4 calls, 1 with it.
    back = _call(db, agent, _booking(6, MISSING_ZIP), days_ago=0, version=16)
    again, step = _since(client, user, issue_id)
    assert (again["calls"], again["calls_with_issue"]) == (4, 1)
    assert again["is_fix"] is True and again["last_call_id"] == str(back)
    assert step.endswith("): 4 calls, 1 with this issue.")
    assert _get(client, user, issue_id)["data"]["state"] == "reopened"
    # A later version counts too.
    _call(db, agent, _booking(7, FULL), days_ago=0, version=17)
    assert _since(client, user, issue_id)[0]["calls"] == 5


def test_a_call_on_an_older_version_reopens_without_being_counted(
    client: TestClient, db: Session
) -> None:
    user, agent, issue_id = _one_issue(db, client)
    assert _fixed(client, user, issue_id, version="16").status_code == 200
    _call(db, agent, _booking(2, FULL), days_ago=0, version=16)
    _call(db, agent, _booking(3, MISSING_ZIP), days_ago=0, version=15)

    since, step = _since(client, user, issue_id)
    assert _get(client, user, issue_id)["data"]["state"] == "reopened"
    assert (since["calls"], since["calls_with_issue"]) == (1, 0)
    assert "reopened by a call that started after that on an older version" in step


def test_since_version_answers_for_any_version_of_an_issue_never_marked_fixed(
    client: TestClient, db: Session
) -> None:
    user, agent, issue_id = _one_issue(db, client)
    _call(db, agent, _booking(2, FULL), days_ago=0, version=16)
    _call(db, agent, _booking(3, MISSING_ZIP), days_ago=0, version=16)

    asked, step = _since(client, user, issue_id, "16")
    assert (asked["version"], asked["is_fix"]) == ("16", False)
    assert (asked["calls"], asked["calls_with_issue"]) == (2, 1)
    assert step.endswith("): 2 calls, 1 with this issue.")
    # Every call ran version 15 or later.
    assert _since(client, user, issue_id, "15")[0]["calls"] == 3
    assert _since(client, user, issue_id, "40")[1] == (
        "Version 40 has not served a real call yet."
    )
    assert _get(client, user, issue_id)["data"]["state"] == "open"

    # Another workspace cannot read it.
    other = _person(db)
    r = client.get(
        f"{API}/mcp/workspaces/{other.company_id}/issues/{issue_id}",
        headers=_headers(other),
        params={"since_version": "16"},
    )
    assert r.status_code == 404


def test_refusals_change_nothing(client: TestClient, db: Session) -> None:
    user, agent, issue_id = _one_issue(db, client)

    found = _fixed(client, user, issue_id, version="15")
    assert found.status_code == 422
    detail = found.json()["detail"]
    assert detail["error"].startswith("This issue was found on 1 call on version 15")
    assert _get(client, user, issue_id)["data"]["state"] == "open"

    # A later number than a version it was found on is fine.
    assert _fixed(client, user, issue_id, version="16").status_code == 200
    same = _fixed(client, user, issue_id, version="16")
    assert same.status_code == 422
    assert "already marked fixed in version 16" in same.json()["detail"]["error"]

    assert (
        client.post(
            f"{_issue_url(user, issue_id)}/archive",
            headers=_headers(user),
            json={"reason": "Known vendor bug"},
        ).status_code
        == 200
    )
    archived = _fixed(client, user, issue_id, version="17")
    assert archived.status_code == 422
    assert archived.json()["detail"]["error"] == "The issue is archived"

    other = _person(db)
    assert _fixed(client, other, issue_id, version="17").status_code == 404
    assert _fixed(client, user, issue_id, version="  ").status_code == 422
