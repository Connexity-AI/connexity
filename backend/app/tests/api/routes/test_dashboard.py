"""The Dashboard (10.191): tiles, calls per day, areas and the onboarding strip, on the
web route and through `get_dashboard`. Calls are invented."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.crud.latency import percentile
from app.services import score as score_service
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


def _dashboard(client: TestClient, user, **params) -> dict:  # noqa: ANN001, ANN003
    response = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/dashboard",
        headers=_headers(user),
        params=params,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_percentiles_are_nearest_rank_in_seconds() -> None:
    gaps = [100 * n for n in range(1, 21)]  # 0.1 s to 2.0 s
    assert percentile(gaps, 0.5) == 1.0
    assert percentile(gaps, 0.95) == 1.9
    assert percentile([800], 0.95) == 0.8


def test_tiles_days_and_areas_for_all_agents_and_one(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(score_service, "onboarding_complete", lambda **_: True)
    user = _person(db)
    front = _agent(db, user, "Front desk")
    night = _agent(db, user, "Night line")
    _call(db, front, _booking(1, FULL))
    _call(db, front, _booking(1, FULL))
    _call(db, front, _booking(1, MISSING_ZIP))
    _call(db, night, _booking(1, FULL))

    body = _dashboard(client, user)
    data = body["data"]

    assert (data["agents_counted"], data["calls"]) == (2, 4)
    assert (data["failed"], data["failed_share"]) == (1, 0.25)
    assert (data["degraded"], data["degraded_share"]) == (0, 0.0)
    assert data["score"]["score"] == 75
    assert len(data["days"]) == 31
    assert sum(day["calls"] for day in data["days"]) == 4
    assert sum(day["failed"] for day in data["days"]) == 1

    areas = {area["key"]: area for area in data["areas"]}
    assert len(areas) == 14
    booking = areas["booking"]
    assert booking["status"] == "critical"
    assert (booking["failed"], booking["share"]) == (1, 0.25)
    assert booking["top_issue_title"].startswith(
        "Booking with missing or placeholder details"
    )
    assert areas["tools_and_integrations"]["status"] == "healthy"
    assert areas["greeting_and_identification"]["status"] == "not_checked"
    assert (
        areas["greeting_and_identification"]["waits_for"]
        == "No check covers this area yet"
    )
    # Critical first, not checked last.
    statuses = [area["status"] for area in data["areas"]]
    assert statuses[0] == "critical" and statuses[-1] == "not_checked"
    assert any("get_issue" in step for step in body["next_steps"])

    one = _dashboard(client, user, agent_id=str(night.id))["data"]
    assert (one["agents_counted"], one["calls"], one["failed"]) == (1, 1, 0)
    assert {a["key"]: a["status"] for a in one["areas"]}["booking"] == "healthy"
    assert one["score"]["score"] == 100


def test_the_strip_shows_while_onboarding_runs(client: TestClient, db: Session) -> None:
    user = _person(db)
    agent = _agent(db, user, "Front desk")
    _call(db, agent, _booking(1, FULL))

    data = _dashboard(client, user)["data"]

    strip = data["onboarding"]
    assert [step["key"] for step in strip["steps"]] == [
        "scan",
        "spec",
        "answers",
        "complete",
    ]
    assert strip["areas_total"] == 14
    assert data["score"]["score"] is None


def test_an_agent_of_another_workspace_is_not_found(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    other = _agent(db, _person(db), "Elsewhere")
    response = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/dashboard",
        headers=_headers(user),
        params={"agent_id": str(other.id)},
    )
    assert response.status_code == 404
