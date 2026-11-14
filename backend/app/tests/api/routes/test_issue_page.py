"""One issue's page, archiving, the spike rule and the Calls page's issue filter, on
invented calls checked by the real engine (plan `plans/2026-11-13-issue-page.md`)."""

import time
import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app import crud
from app.core.config import settings
from app.models import Agent, User
from app.models.check import DecisionRecord, Issue
from app.models.enums import IssueState
from app.services.checks.engine import check_call_safely
from app.services.mappings.retell import retell_call_to_trace
from app.tests.api.routes.test_issues_list import _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _headers,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.utils.retell_payloads import retell_call, speech

API = settings.API_V1_STR
DAY_MS = 86_400_000
MISSING = FULL | {"streetAddress": ""}


def _call(
    db: Session,
    agent: Agent,
    *bookings: list[dict[str, Any]],
    days_ago: float = 1,
    version: int = 7,
    caller: str = "+17325550000",
) -> uuid.UUID:
    payload = retell_call(
        f"call_{uuid.uuid4().hex[:8]}",
        agent_id=agent.platform_agent_id or "",
        timeline=[speech("agent", "Hello", 0.5)] + [e for b in bookings for e in b],
        start_ms=int(time.time() * 1000 - days_ago * DAY_MS),
        agent_version=version,
        from_number=caller,
    )
    stored = crud.store_trace(
        session=db,
        trace=retell_call_to_trace(payload),
        agent_id=agent.id,
        company_id=agent.company_id,
        integration_id=agent.integration_id,
        raw=payload,
    )
    db.commit()
    check_call_safely(session=db, call=stored.call)
    return stored.call.id


def _issue(db: Session, agent: Agent, check_type: str) -> Issue:
    return db.exec(
        select(Issue).where(Issue.agent_id == agent.id, Issue.check_type == check_type)
    ).one()


def _page(client: TestClient, cookies: dict[str, str], issue: Issue) -> Any:
    r = client.get(f"{API}/issues/{issue.id}", cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json()


def _state(
    client: TestClient, cookies: dict[str, str], issue: Issue, **body: Any
) -> Any:
    return client.put(f"{API}/issues/{issue.id}/state", cookies=cookies, json=body)


def _call_result(
    client: TestClient, cookies: dict[str, str], call_id: uuid.UUID
) -> Any:
    r = client.get(f"{API}/calls/{call_id}/screen", cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json()


def test_the_page_shows_size_chain_days_marks_calls_and_history(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    first = _call(db, agent, _booking(1, MISSING), days_ago=40, caller="+17325552207")
    _call(db, agent, _booking(1, MISSING), days_ago=5)
    # Twice in one call: still one call.
    twice = _call(db, agent, _booking(1, MISSING), _booking(2, MISSING), days_ago=2)
    _call(db, agent, _booking(1, FULL), days_ago=2, version=8)
    issue = _issue(db, agent, "booking_details_missing")

    page = _page(client, cookies, issue)

    assert page["title"] == (
        "Booking with missing or placeholder details: schedule_appointment"
    )
    assert (page["agent_name"], page["severity"], page["state"]) == (
        "Front desk",
        "critical",
        "open",
    )
    # The last 30 days: two of the agent's three calls in that time.
    assert (page["tiles"]["calls_affected"], page["tiles"]["calls_total"]) == (2, 3)
    assert page["chain"]["found"]["call_id"] == str(first)
    assert page["chain"]["found"]["caller_last_four"] == "2207"
    assert page["chain"]["fixed"] is None
    assert len(page["days"]) == 30
    assert sum(d["calls"] for d in page["days"]) == 2
    assert page["peak"] == 1
    # Version 8 is a change in the period; version 7 is where the agent started.
    assert [(m["kind"], m["label"]) for m in page["marks"]] == [
        ("version", "Version 8")
    ]
    rows = page["affected_calls"]
    assert [r["call_id"] for r in rows][0] == str(twice)
    assert rows[0]["moment"]["times"] == 2
    assert rows[0]["moment"]["at_seconds"] > 0
    assert rows[0]["result"] == "failed"
    assert [h["kind"] for h in page["history"]] == ["opened"]
    assert page["history"][0]["reason"] == "First seen on call •••• 2207"

    _state(client, cookies, issue, state="resolved", version="v15")
    fixed = _page(client, cookies, issue)["chain"]["fixed"]
    assert fixed["version"] == "v15"


def test_archiving_hides_the_issue_on_every_call_until_it_is_unarchived(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    before = _call(db, agent, _booking(1, MISSING), days_ago=3)
    issue = _issue(db, agent, "booking_details_missing")
    assert _call_result(client, cookies, before)["result"] == "failed"

    refused = _state(client, cookies, issue, state="archived", reason="  ")
    assert refused.status_code == 422
    archived = _state(
        client, cookies, issue, state="archived", reason="Known", duration="forever"
    )
    assert archived.status_code == 200, archived.text
    after = _call(db, agent, _booking(1, MISSING), days_ago=0)

    # Hidden on every call, before and after the archive.
    for call_id in (before, after):
        screen = _call_result(client, cookies, call_id)
        assert screen["findings"] == []
        assert screen["result"] == "clean"
    calls = client.get(f"{API}/calls", cookies=cookies).json()
    assert calls["tiles"]["failed"] == 0
    assert all(c["worst_finding"] is None for c in calls["data"])
    # Still found and stored, and the issue's own page still counts its calls.
    page = _page(client, cookies, issue)
    assert page["tiles"]["calls_affected"] == 2
    assert page["archive"]["duration"] == "forever"
    assert page["archive"]["reason"] == "Known"
    assert page["archive"]["assistant"] is None
    assert page["history"][0]["kind"] == "archived"
    assert [m["kind"] for m in page["marks"]] == ["archived"]

    assert _state(client, cookies, issue, state="open").status_code == 200
    assert _call_result(client, cookies, before)["result"] == "failed"
    assert client.get(f"{API}/calls", cookies=cookies).json()["tiles"]["failed"] == 2
    assert _page(client, cookies, issue)["history"][0]["kind"] == "unarchived"


def _archive_now(db: Session, issue: Issue, user: User, until_spike: bool) -> None:
    crud.set_issue_state(
        session=db,
        issue_id=issue.id,
        state=IssueState.ARCHIVED,
        version=None,
        reason="Known",
        decided_by=user,
        until_spike=until_spike,
    )


def test_an_archived_issue_comes_back_when_it_spikes(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    # Baseline: 2 of 20 calls (10%) in the 30 days before the archive.
    for n in range(20):
        _call(
            db,
            agent,
            _booking(1, MISSING if n < 2 else FULL),
            days_ago=10 + n * 0.5,
        )
    issue = _issue(db, agent, "booking_details_missing")
    _archive_now(db, issue, user, until_spike=True)
    db.refresh(issue)
    assert issue.archive_baseline_share == 0.1

    # Since the archive: 2 of 3 calls is a high share but under 3 calls: no spike.
    _call(db, agent, _booking(1, MISSING), days_ago=0)
    _call(db, agent, _booking(1, MISSING), days_ago=0)
    _call(db, agent, _booking(1, FULL), days_ago=0)
    db.refresh(issue)
    assert issue.state is IssueState.ARCHIVED

    # The third call: 3 of 4 (75%), over twice 10%.
    _call(db, agent, _booking(1, MISSING), days_ago=0)
    db.refresh(issue)
    assert issue.state is IssueState.REOPENED
    record = db.exec(
        select(DecisionRecord)
        .where(DecisionRecord.subject == str(issue.id))
        .order_by(col(DecisionRecord.created_at).desc())
    ).first()
    assert record is not None
    assert (record.old_value, record.new_value) == ("archived", "reopened")
    assert record.decided_by_email == "Connexity"
    assert record.detail is not None and record.detail["calls"] == 3
    assert (
        record.reason == "3 calls this week, 8 times as often as when it was archived"
    )
    page = _page(client, cookies, issue)
    assert page["history"][0]["what"] == "Came back: it spiked"
    assert page["history"][0]["by"] is None
    assert [m["kind"] for m in page["marks"]] == ["archived", "spiked"]


def test_more_calls_at_the_same_share_is_not_a_spike(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    # Baseline: 2 of 10 calls (20%).
    for n in range(10):
        _call(db, agent, _booking(1, MISSING if n < 2 else FULL), days_ago=10 + n)
    issue = _issue(db, agent, "booking_details_missing")
    _archive_now(db, issue, user, until_spike=True)
    # Since the archive the agent is busier: 4 of 20 calls, still 20%. The clean calls
    # come first, so the share never passes 40% on the way.
    for n in range(20):
        _call(db, agent, _booking(1, MISSING if n >= 16 else FULL), days_ago=0)
    db.refresh(issue)
    assert issue.state is IssueState.ARCHIVED


def test_forever_never_comes_back_and_a_zero_baseline_spikes_at_three(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    forever_agent = _agent(db, user, "Forever")
    spike_agent = _agent(db, user, "Stopped")
    for agent in (forever_agent, spike_agent):
        _call(db, agent, _booking(1, MISSING), days_ago=45)
    forever = _issue(db, forever_agent, "booking_details_missing")
    stopped = _issue(db, spike_agent, "booking_details_missing")
    _archive_now(db, forever, user, until_spike=False)
    _archive_now(db, stopped, user, until_spike=True)
    db.refresh(stopped)
    assert stopped.archive_baseline_share == 0.0
    for agent in (forever_agent, spike_agent):
        for _ in range(3):
            _call(db, agent, _booking(1, MISSING), days_ago=0)
    db.refresh(forever)
    db.refresh(stopped)
    assert forever.state is IssueState.ARCHIVED
    assert stopped.state is IssueState.REOPENED
    record = db.exec(
        select(DecisionRecord)
        .where(DecisionRecord.subject == str(stopped.id))
        .order_by(col(DecisionRecord.created_at).desc())
    ).first()
    assert record is not None
    assert record.reason == "3 calls this week; it had stopped when it was archived"


def test_the_calls_page_filtered_to_an_issue_shows_each_calls_moment(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    twice = _call(db, agent, _booking(1, MISSING), _booking(2, MISSING), days_ago=1)
    _call(db, agent, _booking(1, FULL), days_ago=1)
    issue = _issue(db, agent, "booking_details_missing")

    body = client.get(
        f"{API}/calls", cookies=cookies, params={"issue_id": str(issue.id)}
    ).json()
    assert [c["id"] for c in body["data"]] == [str(twice)]
    assert body["tiles"]["calls"] == 1
    assert body["data"][0]["moment"]["times"] == 2
    assert body["issue"]["label"].startswith("Booking with missing")
    unfiltered = client.get(f"{API}/calls", cookies=cookies).json()
    assert all(c["moment"] is None for c in unfiltered["data"])


def test_mcp_reads_archives_and_unarchives_an_issue(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Front desk")
    call_id = _call(db, agent, _booking(1, MISSING), days_ago=1)
    issue = _issue(db, agent, "booking_details_missing")
    base = f"{API}/mcp/workspaces/{user.company_id}/issues/{issue.id}"
    headers = _headers(user)

    read = client.get(base, headers=headers)
    assert read.status_code == 200, read.text
    body = read.json()
    assert body["data"]["tiles"]["calls_affected"] == 1
    assert any("archive_issue" in s for s in body["next_steps"])
    assert any("wait for the person's yes" in r for r in body["rules"])

    calls = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/calls",
        headers=headers,
        params={"issue_id": str(issue.id)},
    ).json()
    assert [c["id"] for c in calls["data"]["calls"]] == [str(call_id)]
    assert calls["data"]["calls"][0]["moment"]["times"] == 1

    assert client.post(f"{base}/archive", headers=headers, json={}).status_code == 422
    archived = client.post(
        f"{base}/archive",
        headers=headers,
        json={"reason": "Dmytro: callers hang up during hold music"},
    )
    assert archived.status_code == 200, archived.text
    data = archived.json()["data"]
    assert data["state"] == "archived"
    assert data["archive"]["duration"] == "until_spike"
    assert data["archive"]["assistant"] == "your assistant"
    record = db.exec(
        select(DecisionRecord).where(DecisionRecord.subject == str(issue.id))
    ).one()
    assert record.decided_by == user.id
    # Hidden from the assistant on calls too.
    hidden = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/calls/{call_id}", headers=headers
    ).json()
    assert hidden["data"]["findings"] == []

    back = client.post(f"{base}/unarchive", headers=headers, json={})
    assert back.status_code == 200, back.text
    assert back.json()["data"]["state"] == "open"
    again = client.post(f"{base}/unarchive", headers=headers, json={}).json()
    assert any("nothing changed" in s for s in again["next_steps"])

    other = _person(db)
    stranger = client.get(base, headers=_headers(other))
    assert stranger.status_code == 404
    missing = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/issues/{uuid.uuid4()}",
        headers=headers,
    )
    assert missing.status_code == 404


def test_another_workspace_cannot_read_or_archive_an_issue(
    client: TestClient, db: Session
) -> None:
    _, cookies = _signed_in(client, db)
    other = _person(db)
    agent = _agent(db, other, "Elsewhere")
    _call(db, agent, _booking(1, MISSING))
    issue = _issue(db, agent, "booking_details_missing")

    assert client.get(f"{API}/issues/{issue.id}", cookies=cookies).status_code == 404
    assert (
        _state(client, cookies, issue, state="archived", reason="x").status_code == 404
    )
    db.refresh(issue)
    assert issue.state is IssueState.OPEN


def test_calls_from_before_the_archive_never_make_a_spike(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    # A busy week just before the archive: 3 of 6 calls, against a lower 30-day share.
    for n in range(20):
        _call(db, agent, _booking(1, FULL), days_ago=10 + n * 0.5)
    for n in range(6):
        _call(db, agent, _booking(1, MISSING if n < 3 else FULL), days_ago=2)
    issue = _issue(db, agent, "booking_details_missing")
    _archive_now(db, issue, user, until_spike=True)
    # One more finding after the archive: only 1 call since then, so no spike.
    _call(db, agent, _booking(1, MISSING), days_ago=0)
    db.refresh(issue)
    assert issue.state is IssueState.ARCHIVED


def test_archiving_an_archived_issue_through_mcp_changes_nothing(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Front desk")
    _call(db, agent, _booking(1, MISSING), days_ago=1)
    issue = _issue(db, agent, "booking_details_missing")
    base = f"{API}/mcp/workspaces/{user.company_id}/issues/{issue.id}"
    headers = _headers(user)
    first = client.post(f"{base}/archive", headers=headers, json={"reason": "Known"})
    assert first.status_code == 200, first.text

    again = client.post(
        f"{base}/archive",
        headers=headers,
        json={"reason": "Known", "duration": "forever"},
    )

    assert again.status_code == 200
    assert again.json()["data"]["archive"]["duration"] == "until_spike"
    assert any("nothing changed" in s for s in again.json()["next_steps"])
    records = db.exec(
        select(DecisionRecord).where(DecisionRecord.subject == str(issue.id))
    ).all()
    assert len(records) == 1
