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
    assert "and live" in live["next_steps"][0]
    rows = _issues(client, user, status="resolved").json()["data"]["issues"]
    assert rows[0]["fix_live"] is True

    # Found again on version 17: reopened, and the assistant is told.
    _call(db, agent, _booking(4, MISSING_ZIP), days_ago=0, version=17)
    back = _get(client, user, issue_id)
    assert back["data"]["state"] == "reopened"
    assert back["data"]["history"][0]["reason"] == (
        "Came back on version 17, after the fix in version 16 went live"
    )
    assert "came back after the fix in version 16" in back["next_steps"][0]
    assert "`mark_issue_fixed`" in back["next_steps"][0]

    # Marking it fixed again in a later version works.
    again = _fixed(client, user, issue_id, version="18")
    assert again.status_code == 200, again.text
    assert again.json()["data"]["state"] == "resolved"


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
