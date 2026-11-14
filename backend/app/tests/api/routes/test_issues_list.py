"""The Issues page (`GET /issues`), on invented calls checked by the real engine."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User
from app.models.check import Issue
from app.models.enums import IssueState
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _call,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.utils.retell_payloads import invocation, result
from app.tests.utils.utils import extract_cookies, random_email, random_lower_string

API = settings.API_V1_STR


def _signed_in(client: TestClient, db: Session) -> tuple[User, dict[str, str]]:
    email, password = random_email(), random_lower_string()
    signup = client.post(
        f"{API}/users/signup", json={"email": email, "password": password}
    )
    assert signup.status_code == 200, signup.text
    login = client.post(
        f"{API}/login/access-token", data={"username": email, "password": password}
    )
    user = db.exec(select(User).where(User.email == email)).one()
    return user, extract_cookies(login)


def _failed_tool(n: int) -> list[dict[str, object]]:
    return [
        invocation(f"f{n}", "check_slots", "{}", time_sec=1.0 + n),
        result(f"f{n}", '{"error": "timeout"}', successful=False, time_sec=1.5 + n),
    ]


def _page(client: TestClient, cookies: dict[str, str], **params: str) -> dict:
    r = client.get(f"{API}/issues", cookies=cookies, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _rows(body: dict) -> list[tuple[str, str, str]]:
    return [
        (group["category"]["value"], issue["check_type"], issue["state"])
        for group in body["groups"]
        for issue in group["issues"]
    ]


def test_issues_are_grouped_by_category_worst_first_with_tiles(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    desk = _agent(db, user, "Front desk")
    other = _agent(db, user, "Night line")
    # Front desk: three calls with placeholder details, one with a double booking, and
    # one failed tool call. Night line: one call, with placeholder details.
    _call(db, desk, _booking(1, FULL | {"streetAddress": ""}), _failed_tool(5))
    _call(db, desk, _booking(1, FULL | {"full_name": "{{full_name}}"}))
    _call(db, desk, _booking(1, FULL | {"postalCode": ""}), _booking(2, FULL | {}))
    _call(db, desk, _booking(1, FULL))
    _call(db, other, _booking(1, FULL | {"streetAddress": ""}))
    _call(db, other, _booking(1, FULL))

    body = _page(client, cookies)

    # Booking comes before Tools and integrations, in the categories' fixed order.
    assert [g["category"]["value"] for g in body["groups"]] == [
        "booking",
        "tools_and_integrations",
    ]
    booking = body["groups"][0]
    # Worst first inside the group: by calls affected among the critical ones.
    assert [(i["agent_name"], i["check_type"]) for i in booking["issues"]] == [
        ("Front desk", "booking_details_missing"),
        ("Night line", "booking_details_missing"),
        ("Front desk", "booking_duplicated"),
    ]
    first = booking["issues"][0]
    assert (first["calls_affected"], first["calls_total"]) == (3, 4)
    assert first["severity"] == "critical"
    assert first["found_by"] == "rule"
    assert first["title"] == (
        "Booking with missing or placeholder details: schedule_appointment"
    )
    # A call two issues of one group share counts once.
    assert (booking["issue_count"], booking["calls_affected"]) == (3, 4)
    assert booking["critical"] == 3
    assert body["tiles"] == {
        "open": 4,
        "critical": 4,
        "reopened": 0,
        "resolved": 0,
        "calls_affected": 4,
        "calls": 6,
    }
    assert (body["total"], body["truncated"], body["status"]) == (4, False, "open")
    assert [a["label"] for a in body["agents"]] == ["Front desk", "Night line"]
    assert len(body["categories"]) == 14


def test_filters_and_search_leave_the_tiles_alone(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    desk = _agent(db, user, "Front desk")
    other = _agent(db, user, "Night line")
    _call(db, desk, _booking(1, FULL | {"streetAddress": ""}), _failed_tool(5))
    _call(db, other, _booking(1, FULL), _booking(2, FULL))
    everything = _page(client, cookies)
    tiles = everything["tiles"]
    duplicated = next(
        i
        for g in everything["groups"]
        for i in g["issues"]
        if i["check_type"] == "booking_duplicated"
    )

    def types(**params: str) -> list[str]:
        body = _page(client, cookies, **params)
        if "agent_id" not in params and "period" not in params:
            assert body["tiles"] == tiles
        return [check for _, check, _ in _rows(body)]

    assert types(category="tools_and_integrations") == ["tool_call_failed"]
    # One call each, so their order within Booking is by when they were last seen.
    assert sorted(types(severity="critical")) == [
        "booking_details_missing",
        "booking_duplicated",
        "tool_call_failed",
    ]
    assert types(q="TWO bookings") == ["booking_duplicated"]
    assert types(q=duplicated["id"]) == ["booking_duplicated"]
    assert types(q="nothing like this") == []
    assert types(agent_id=str(other.id)) == ["booking_duplicated"]
    assert _page(client, cookies, agent_id=str(other.id))["tiles"]["calls"] == 1


def test_states_and_the_period(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    desk = _agent(db, user, "Front desk")
    _call(db, desk, _booking(1, FULL | {"streetAddress": ""}), _failed_tool(5))
    _call(db, desk, _booking(1, FULL), _booking(2, FULL))
    _call(db, desk, _failed_tool(1), days_ago=40)
    issues = {
        i.check_type: i
        for i in db.exec(select(Issue).where(Issue.agent_id == desk.id)).all()
    }

    def state(check: str, value: str, reason: str | None = None) -> None:
        r = client.put(
            f"{API}/issues/{issues[check].id}/state",
            cookies=cookies,
            json={"state": value, "version": "v15", "reason": reason},
        )
        assert r.status_code == 200, r.text

    state("booking_duplicated", "resolved")
    state("tool_call_failed", "archived", "Vendor bug, known")
    # Resolved, then found again on a later call: reopened.
    state("booking_details_missing", "resolved")
    _call(db, desk, _booking(1, FULL | {"postalCode": ""}), days_ago=0)

    body = _page(client, cookies)
    assert _rows(body) == [("booking", "booking_details_missing", "reopened")]
    assert body["tiles"]["reopened"] == 1
    assert body["tiles"]["resolved"] == 1
    assert _rows(_page(client, cookies, status="reopened")) == _rows(body)
    resolved = _page(client, cookies, status="resolved")
    assert _rows(resolved) == [("booking", "booking_duplicated", "resolved")]
    assert resolved["groups"][0]["issues"][0]["resolved_version"] == "v15"
    archived = _page(client, cookies, status="archived")
    assert _rows(archived) == [
        ("tools_and_integrations", "tool_call_failed", "archived")
    ]
    # Calls affected counts the period: the 40-day-old call is in 90 days only.
    assert archived["groups"][0]["issues"][0]["calls_affected"] == 1
    longer = _page(client, cookies, status="archived", period="90d")
    assert longer["groups"][0]["issues"][0]["calls_affected"] == 2

    # A resolved issue shows only when it was resolved in the period.
    duplicated = db.get(Issue, issues["booking_duplicated"].id)
    assert duplicated is not None and duplicated.state is IssueState.RESOLVED
    duplicated.resolved_at = datetime.now(UTC) - timedelta(days=10)
    db.add(duplicated)
    db.commit()
    assert _rows(_page(client, cookies, status="resolved", period="7d")) == []
    assert _page(client, cookies, period="7d")["tiles"]["resolved"] == 0
    assert len(_rows(_page(client, cookies, status="resolved"))) == 1


def test_only_the_open_workspaces_issues(client: TestClient, db: Session) -> None:
    _, cookies = _signed_in(client, db)
    other = _person(db)
    elsewhere = _agent(db, other, "Elsewhere")
    _call(db, elsewhere, _booking(1, FULL | {"streetAddress": ""}))
    theirs = db.exec(select(Issue).where(Issue.agent_id == elsewhere.id)).one()

    body = _page(client, cookies)
    assert body["groups"] == []
    assert body["tiles"]["calls"] == 0
    assert _page(client, cookies, q=str(theirs.id))["groups"] == []
    assert client.get(f"{API}/issues").status_code == 401
    assert (
        client.get(f"{API}/issues", cookies=cookies, params={"status": "accepted"})
    ).status_code == 422
