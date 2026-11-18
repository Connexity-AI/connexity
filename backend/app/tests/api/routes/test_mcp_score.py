"""The score (10.19): the formula, what moves it, and how get_agent and list_agents
answer it. Calls are invented."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.crud.score import ShownFinding
from app.services import score as score_service
from app.services.score import _moves, score_of
from app.tests.api.routes.test_mcp_issues import (
    API,
    FULL,
    _agent,
    _booking,
    _call,
    _headers,
    _person,
    _settings,  # noqa: F401 - the autouse fixture that sets up MCP sign-in
)

MISSING_ZIP = {**FULL, "postalCode": ""}


def test_the_formula() -> None:
    assert score_of(failed=2, degraded=2, checked=10) == 70
    assert score_of(failed=0, degraded=0, checked=4) == 100
    assert score_of(failed=3, degraded=0, checked=3) == 0
    # Halves round up, always: 82.5 -> 83 and 83.5 -> 84.
    assert score_of(failed=7, degraded=0, checked=40) == 83
    assert score_of(failed=33, degraded=0, checked=200) == 84
    # No checked call: no score, never 100 by default.
    assert score_of(failed=0, degraded=0, checked=0) is None


def test_what_moves_it_is_the_rise_without_each_issue(db: Session) -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    agent = uuid.uuid4()
    one, two, three = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    findings = [
        ShownFinding(one, agent, a, fails=True),
        ShownFinding(two, agent, b, fails=False),
        # A call failed by a and degraded by b: without a it is still degraded.
        ShownFinding(three, agent, a, fails=True),
        ShownFinding(three, agent, b, fails=False),
    ]
    moves = _moves(db, findings, checked=10)
    # a: call one 1 -> 0, call three 1 -> 0.5; b: call two 0.5 -> 0, call three none.
    assert [(m.issue_id, m.points, m.calls) for m in moves] == [
        (a, 15.0, 2),
        (b, 5.0, 2),
    ]


@pytest.fixture
def onboarded(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routes import mcp

    monkeypatch.setattr(score_service, "onboarding_complete", lambda **_: True)
    monkeypatch.setattr(mcp, "onboarding_complete", lambda **_: True)


def _get_agent(client: TestClient, user, agent_id) -> dict:  # noqa: ANN001
    response = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents/{agent_id}",
        headers=_headers(user),
    )
    assert response.status_code == 200
    return response.json()


def test_get_agent_answers_the_score_its_change_and_what_moves_it(
    client: TestClient, db: Session, onboarded: None
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, FULL))
    _call(db, agent, _booking(1, FULL))
    _call(db, agent, _booking(1, MISSING_ZIP))
    # The previous 30 days: one failed call, score 0.
    _call(db, agent, _booking(1, MISSING_ZIP), days_ago=40)

    body = _get_agent(client, user, agent.id)

    score = body["data"]["score"]
    assert (score["score"], score["checked_calls"], score["failed_calls"]) == (67, 3, 1)
    assert (score["previous"], score["change"]) == (0, 67)
    (move,) = score["moves"]
    assert move["title"].startswith("Booking with missing or placeholder details")
    assert (move["points"], move["calls"]) == (33.3, 1)
    assert any("costs the score most" in step for step in body["next_steps"])
    assert any("0.5 x degraded" in rule for rule in body["rules"])


def test_each_agents_score_and_the_workspaces(
    client: TestClient, db: Session, onboarded: None
) -> None:
    user = _person(db)
    first = _agent(db, user, "First")
    second = _agent(db, user, "Second")
    _call(db, first, _booking(1, FULL))
    _call(db, second, _booking(1, MISSING_ZIP))

    body = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents", headers=_headers(user)
    ).json()

    scores = {row["name"]: row["score"] for row in body["data"]}
    assert scores == {"First": 100, "Second": 0}
    # The answer keeps the standard shape; the workspace's score is on its row.
    assert set(body) == {"data", "rules", "next_steps", "guide", "next_cursor"}
    workspaces = client.get(f"{API}/mcp/workspaces", headers=_headers(user)).json()
    (row,) = (w for w in workspaces["data"] if w["id"] == str(user.company_id))
    assert row["score"] == 50


def test_no_score_before_onboarding_is_complete(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, MISSING_ZIP))

    score = _get_agent(client, user, agent.id)["data"]["score"]

    assert score["score"] is None
    assert "after onboarding" in score["why_none"]
    assert score["checked_calls"] == 1


def test_archiving_lifts_the_score_and_unarchiving_lowers_it(
    client: TestClient, db: Session, onboarded: None
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, FULL))
    _call(db, agent, _booking(1, MISSING_ZIP))
    base = f"{API}/mcp/workspaces/{user.company_id}"
    (issue,) = client.get(f"{base}/issues", headers=_headers(user)).json()["data"][
        "issues"
    ]
    assert _get_agent(client, user, agent.id)["data"]["score"]["score"] == 50

    archived = client.post(
        f"{base}/issues/{issue['id']}/archive",
        headers=_headers(user),
        json={"reason": "Invented reason", "duration": "forever"},
    )
    assert archived.status_code == 200
    assert _get_agent(client, user, agent.id)["data"]["score"]["score"] == 100

    client.post(
        f"{base}/issues/{issue['id']}/unarchive", headers=_headers(user), json={}
    )
    assert _get_agent(client, user, agent.id)["data"]["score"]["score"] == 50
