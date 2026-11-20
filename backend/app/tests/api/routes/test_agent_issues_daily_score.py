"""The agent page's daily score, Issues tile and tab, and the Issues page's version
filter (10.1993), on invented calls (plan `plans/2026-11-20-agent-issues-daily-score.md`)."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.services import score as score_service
from app.tests.api.routes.test_issues_list import _failed_tool, _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    API,
    FULL,
    _agent,
    _booking,
    _call,
    _headers,
    _settings,  # the autouse fixture that sets an encryption key
)

MISSING_ZIP = {**FULL, "postalCode": ""}


@pytest.fixture
def onboarded(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routes import mcp
    from app.services import agent_page

    monkeypatch.setattr(score_service, "onboarding_complete", lambda **_: True)
    monkeypatch.setattr(agent_page, "onboarding_complete", lambda **_: True)
    monkeypatch.setattr(mcp, "onboarding_complete", lambda **_: True)


def _page(client: TestClient, cookies: dict[str, str], agent_id, **params: str) -> dict:  # noqa: ANN001
    r = client.get(f"{API}/agents/{agent_id}/page", cookies=cookies, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _issues(client: TestClient, cookies: dict[str, str], **params: str) -> dict:
    r = client.get(f"{API}/issues", cookies=cookies, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _scored(page: dict) -> list[tuple[int | None, int]]:
    return [
        (d["score"], d["checked_calls"])
        for d in page["latency_days"]
        if d["checked_calls"] or d["score"] is not None
    ]


def test_each_day_has_its_score_over_its_checked_calls(
    client: TestClient, db: Session, onboarded: None
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, FULL), days_ago=3)
    _call(db, agent, _booking(2, MISSING_ZIP), days_ago=3)
    _call(db, agent, _booking(3, FULL), days_ago=1)

    page = _page(client, cookies, agent.id)

    # Oldest day first: 50 over two checked calls, then 100 over one.
    assert _scored(page) == [(50, 2), (100, 1)]
    # Every other day of the period has no score.
    assert sum(1 for d in page["latency_days"] if d["score"] is None) == (
        len(page["latency_days"]) - 2
    )
    # The assistant gets the same days.
    mcp = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents/{agent.id}",
        headers=_headers(user),
    ).json()
    assert _scored(mcp["data"]) == [(50, 2), (100, 1)]
    assert any("checked_calls" in rule for rule in mcp["rules"])


def test_no_daily_score_before_onboarding(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, MISSING_ZIP))

    page = _page(client, cookies, agent.id)

    assert _scored(page) == []
    assert "onboarding" in page["score"]["why_none"]


def test_issues_tile_and_tab_match_the_issues_page_with_and_without_a_version(
    client: TestClient, db: Session, onboarded: None
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Invented")
    other = _agent(db, user, "Elsewhere")
    _call(db, agent, _booking(1, MISSING_ZIP), days_ago=2, version=87)
    _call(db, agent, _failed_tool(1), days_ago=1, version=88)
    _call(db, other, _booking(1, MISSING_ZIP))

    whole = _page(client, cookies, agent.id)
    listed = _issues(client, cookies, agent_id=str(agent.id))
    # Both are critical (code checks): the open count is the Issues page's Open tile.
    assert (whole["open_issues"], whole["critical_issues"]) == (2, 2)
    assert (listed["tiles"]["open"], listed["tiles"]["critical"]) == (2, 2)
    # The agent's versions to filter by, the latest call's first.
    assert [v["version"] for v in listed["versions"]] == ["88", "87"]
    assert listed["version"] is None

    on_87 = _page(client, cookies, agent.id, version="87")
    listed_87 = _issues(client, cookies, agent_id=str(agent.id), version="87")
    assert (on_87["open_issues"], on_87["critical_issues"]) == (1, 1)
    assert (listed_87["tiles"]["open"], listed_87["tiles"]["critical"]) == (1, 1)
    assert listed_87["version"] == "87"
    (group,) = listed_87["groups"]
    (row,) = group["issues"]
    assert row["severity"] == "critical"
    assert row["first_seen_at"] is not None

    on_88 = _issues(client, cookies, agent_id=str(agent.id), version="88")
    assert (on_88["tiles"]["open"], on_88["tiles"]["critical"]) == (1, 1)
    assert on_88["groups"][0]["issues"][0]["title"] != row["title"]

    # The assistant gets the same counts.
    mcp = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents/{agent.id}",
        headers=_headers(user),
        params={"version": "87"},
    ).json()
    assert (mcp["data"]["open_issues"], mcp["data"]["critical_issues"]) == (1, 1)


def test_a_picked_version_scores_only_its_days(
    client: TestClient, db: Session, onboarded: None
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, MISSING_ZIP), days_ago=3, version=87)
    _call(db, agent, _booking(2, FULL), days_ago=1, version=88)

    assert _scored(_page(client, cookies, agent.id, version="88")) == [(100, 1)]
    assert _scored(_page(client, cookies, agent.id, version="87")) == [(0, 1)]


def test_another_workspaces_agent_lists_no_versions(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    stranger, _ = _signed_in(client, db)
    theirs = _agent(db, stranger, "Theirs")
    _call(db, theirs, _booking(1, FULL), version=5)

    listed = _issues(client, cookies, agent_id=str(theirs.id))

    assert listed["versions"] == []
    assert listed["tiles"]["open"] == 0
