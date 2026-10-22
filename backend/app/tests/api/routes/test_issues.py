"""Issues, call status, skipped checks and checking stored calls."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import Agent, CallCheck, DecisionRecord
from app.models.trace import Trace
from app.tests.api.routes.test_checks import (
    CHECK,
    _agent,
    _other_company,
    _read,
    _send,
    _set,
    _trace,
)

API = settings.API_V1_STR


@pytest.fixture(scope="module")
def token(client: TestClient, auth_cookies: dict[str, str]) -> str:
    r = client.post(
        f"{API}/ingest-tokens/", json={"name": "issues"}, cookies=auth_cookies
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _issues(
    client: TestClient, cookies: dict[str, str], agent_id: str
) -> list[dict[str, Any]]:
    r = client.get(f"{API}/agents/{agent_id}/issues", cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json()


def _state(
    client: TestClient,
    cookies: dict[str, str],
    issue_id: str,
    state: str,
    reason: str | None = None,
    version: str | None = None,
) -> Any:
    return client.put(
        f"{API}/issues/{issue_id}/state",
        json={"state": state, "reason": reason, "version": version},
        cookies=cookies,
    )


def _status(client: TestClient, cookies: dict[str, str], call_id: str) -> str:
    r = client.get(f"{API}/calls/{call_id}", cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json()["check_status"]


def _later() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=1)


# ── Findings become issues ─────────────────────────────────────────


def test_the_same_failure_on_three_calls_is_one_issue_and_another_tool_is_a_second(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    calls = [_send(client, token, agent_id, _trace()) for _ in range(3)]
    other = _send(client, token, agent_id, _trace(tool="send_text"))
    _send(client, token, agent_id, _trace(tool_status="ok"))

    issues = {issue["key"]: issue for issue in _issues(client, auth_cookies, agent_id)}

    assert set(issues) == {"find_table", "send_text"}
    issue = issues["find_table"]
    assert (issue["check_type"], issue["title"]) == (CHECK, "Tool call failed")
    assert issue["state"] == "open"
    assert (issue["finding_count"], issue["call_count"]) == (3, 3)
    assert issue["first_seen_at"] <= issue["last_seen_at"]
    assert issues["send_text"]["call_count"] == 1

    r = client.get(f"{API}/issues/{issue['id']}", cookies=auth_cookies)
    assert r.status_code == 200, r.text
    detail = r.json()
    assert {f["call_id"] for f in detail["findings"]} == set(calls)
    assert detail["findings"][0]["event_ids"] == ["t1"]
    assert detail["findings"][0]["effect"] == "fails"
    # Each finding on the call names its issue.
    (finding,) = _read(client, auth_cookies, calls[0])["findings"]
    assert finding["issue_id"] == issue["id"]
    (elsewhere,) = _read(client, auth_cookies, other)["findings"]
    assert elsewhere["issue_id"] == issues["send_text"]["id"]


def test_sending_a_call_again_does_not_add_to_its_issue(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    trace = _trace()
    _send(client, token, agent_id, trace)
    _send(client, token, agent_id, trace)

    (issue,) = _issues(client, auth_cookies, agent_id)
    assert (issue["finding_count"], issue["call_count"]) == (1, 1)


def test_an_issue_outlives_its_findings(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    trace = _trace()
    _send(client, token, agent_id, trace)
    _send(
        client, token, agent_id, {**trace, "events": _trace(tool_status="ok")["events"]}
    )

    (issue,) = _issues(client, auth_cookies, agent_id)
    assert (issue["finding_count"], issue["call_count"]) == (0, 0)
    assert (issue["first_seen_at"], issue["last_seen_at"]) == (None, None)


# ── Call status ────────────────────────────────────────────────────


def test_a_call_is_failed_degraded_clean_or_unchecked(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    failed = _send(client, token, agent_id, _trace())
    clean = _send(client, token, agent_id, _trace(tool_status="ok"))
    no_results = _send(client, token, agent_id, _trace(tool_status=None))
    before_the_check = _send(
        client, token, agent_id, _trace(started_at=datetime(2020, 1, 1, tzinfo=UTC))
    )
    assert _set(client, auth_cookies, agent_id, "flags", "testing").status_code == 200
    degraded = _send(client, token, agent_id, _trace(started_at=_later()))
    assert _set(client, auth_cookies, agent_id, "off", "testing").status_code == 200
    off = _send(client, token, agent_id, _trace(started_at=_later()))

    assert _status(client, auth_cookies, failed) == "failed"
    assert _status(client, auth_cookies, clean) == "clean"
    assert _status(client, auth_cookies, degraded) == "degraded"
    assert _status(client, auth_cookies, no_results) == "unchecked"
    assert _status(client, auth_cookies, off) == "unchecked"
    # A retroactive finding is shown on the call and counts for nothing.
    assert _status(client, auth_cookies, before_the_check) == "clean"

    listed = client.get(f"{API}/agents/{agent_id}/calls", cookies=auth_cookies).json()
    assert {item["id"]: item["check_status"] for item in listed["data"]} == {
        failed: "failed",
        clean: "clean",
        degraded: "degraded",
        no_results: "unchecked",
        off: "unchecked",
        before_the_check: "clean",
    }


def test_a_check_is_skipped_on_a_call_that_lacks_what_it_needs(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    trace = _trace()
    call_id = _send(client, token, agent_id, trace)
    assert len(_read(client, auth_cookies, call_id)["findings"]) == 1

    # The same call sent again without tool results: nothing can be said about it now.
    _send(
        client, token, agent_id, {**trace, "events": _trace(tool_status=None)["events"]}
    )

    body = _read(client, auth_cookies, call_id)
    (check,) = body["checks"]
    assert (check["outcome"], check["missing"]) == ("skipped", "tool_results")
    assert body["findings"] == []
    assert _status(client, auth_cookies, call_id) == "unchecked"


# ── Resolving, regressing, accepting ───────────────────────────────


def test_a_resolved_issue_regresses_only_on_a_call_that_started_afterwards(
    client: TestClient, auth_cookies: dict[str, str], token: str, db: Session
) -> None:
    agent_id = _agent(client, auth_cookies)
    earlier = datetime.now(UTC) - timedelta(minutes=5)
    _send(client, token, agent_id, _trace())
    (issue,) = _issues(client, auth_cookies, agent_id)

    r = _state(client, auth_cookies, issue["id"], "resolved", version="agent v12")
    assert r.status_code == 200, r.text
    resolved = r.json()
    assert (resolved["state"], resolved["resolved_version"]) == (
        "resolved",
        "agent v12",
    )
    assert resolved["resolved_at"] is not None

    # A failing call that started before the fix and arrived late changes nothing.
    _send(client, token, agent_id, _trace(started_at=earlier))
    (still,) = _issues(client, auth_cookies, agent_id)
    assert (still["state"], still["call_count"]) == ("resolved", 2)

    _send(client, token, agent_id, _trace(started_at=_later()))
    (after,) = _issues(client, auth_cookies, agent_id)
    assert (after["state"], after["call_count"]) == ("regressed", 3)
    # What it was resolved in is kept as history.
    assert after["resolved_version"] == "agent v12"

    (record,) = db.exec(
        select(DecisionRecord).where(DecisionRecord.subject == issue["id"])
    ).all()
    assert (record.kind, record.old_value, record.new_value) == (
        "issue_state",
        "open",
        "resolved",
    )
    assert record.decided_by_email
    assert str(record.agent_id) == agent_id


def test_accepting_needs_a_reason_and_an_accepted_issue_stays_accepted(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    _send(client, token, agent_id, _trace())
    (issue,) = _issues(client, auth_cookies, agent_id)

    for reason in (None, "   "):
        refused = _state(client, auth_cookies, issue["id"], "accepted", reason)
        assert refused.status_code == 422, refused.text
        assert "reason is required" in refused.json()["detail"]
    assert _issues(client, auth_cookies, agent_id)[0]["state"] == "open"

    accepted = _state(
        client, auth_cookies, issue["id"], "accepted", "Known, vendor bug"
    )
    assert accepted.status_code == 200, accepted.text
    _send(client, token, agent_id, _trace(started_at=_later()))
    (after,) = _issues(client, auth_cookies, agent_id)
    assert (after["state"], after["call_count"]) == ("accepted", 2)

    decisions = client.get(f"{API}/agents/{agent_id}/decisions", cookies=auth_cookies)
    (record,) = decisions.json()
    assert (record["kind"], record["subject"]) == ("issue_state", issue["id"])
    assert (record["old_value"], record["new_value"]) == ("open", "accepted")
    assert record["reason"] == "Known, vendor bug"


def test_an_issue_can_be_reopened_and_cannot_be_set_to_regressed(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    _send(client, token, agent_id, _trace())
    (issue,) = _issues(client, auth_cookies, agent_id)

    assert _state(client, auth_cookies, issue["id"], "regressed").status_code == 422
    assert _state(client, auth_cookies, issue["id"], "sometimes").status_code == 422
    assert _state(client, auth_cookies, issue["id"], "resolved").status_code == 200
    reopened = _state(client, auth_cookies, issue["id"], "open")
    assert (reopened.status_code, reopened.json()["state"]) == (200, "open")
    # Setting it to what it already is records nothing.
    assert _state(client, auth_cookies, issue["id"], "open").status_code == 200

    decisions = client.get(f"{API}/agents/{agent_id}/decisions", cookies=auth_cookies)
    assert [(d["old_value"], d["new_value"]) for d in decisions.json()] == [
        ("resolved", "open"),
        ("open", "resolved"),
    ]


def test_another_company_cannot_read_or_change_an_issue(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    _send(client, token, agent_id, _trace())
    (issue,) = _issues(client, auth_cookies, agent_id)
    stranger = _other_company(client)

    assert (
        client.get(f"{API}/agents/{agent_id}/issues", cookies=stranger).status_code
        == 404
    )
    assert (
        client.get(f"{API}/issues/{issue['id']}", cookies=stranger).status_code == 404
    )
    assert _state(client, stranger, issue["id"], "resolved").status_code == 404
    assert (
        client.post(f"{API}/agents/{agent_id}/checks/run", cookies=stranger).status_code
        == 404
    )
    assert (
        client.get(f"{API}/issues/{uuid.uuid4()}", cookies=auth_cookies).status_code
        == 404
    )
    assert _issues(client, auth_cookies, agent_id)[0]["state"] == "open"


# ── Stored calls that were never checked ───────────────────────────


def _store_unchecked(db: Session, agent_id: str, trace: dict[str, Any]) -> uuid.UUID:
    agent = db.get(Agent, uuid.UUID(agent_id))
    assert agent is not None
    return crud.store_trace(
        session=db,
        trace=Trace.model_validate(trace),
        agent_id=agent.id,
        company_id=agent.company_id,
    ).call.id


def test_stored_calls_never_checked_are_checked_on_request_and_only_once(
    client: TestClient, auth_cookies: dict[str, str], token: str, db: Session
) -> None:
    agent_id = _agent(client, auth_cookies)
    already = _send(client, token, agent_id, _trace(tool_status="ok"))
    stored = [
        _store_unchecked(db, agent_id, _trace()),
        _store_unchecked(db, agent_id, _trace(tool_status=None)),
    ]
    assert _status(client, auth_cookies, str(stored[0])) == "unchecked"
    before = db.get(CallCheck, (uuid.UUID(already), CHECK))
    assert before is not None

    first = client.post(f"{API}/agents/{agent_id}/checks/run", cookies=auth_cookies)
    second = client.post(f"{API}/agents/{agent_id}/checks/run", cookies=auth_cookies)

    assert first.status_code == 200, first.text
    assert first.json() == {"checked": 2, "remaining": 0}
    # A skipped call has its row too, so it is not picked up again.
    assert second.json() == {"checked": 0, "remaining": 0}
    assert _status(client, auth_cookies, str(stored[0])) == "failed"
    assert _status(client, auth_cookies, str(stored[1])) == "unchecked"
    (issue,) = _issues(client, auth_cookies, agent_id)
    assert issue["call_count"] == 1
    db.expire_all()
    untouched = db.get(CallCheck, (uuid.UUID(already), CHECK))
    assert untouched is not None
    assert untouched.ran_at == before.ran_at


def test_opening_an_agents_calls_checks_the_ones_never_checked(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _agent(client, auth_cookies)
    stored = _store_unchecked(db, agent_id, _trace())

    # The list is answered first; the background pass runs after the response.
    client.get(f"{API}/agents/{agent_id}/calls", cookies=auth_cookies)

    assert _status(client, auth_cookies, str(stored)) == "failed"


def test_a_stored_call_that_cannot_be_checked_at_all_is_not_tried_forever(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent_id = _agent(client, auth_cookies)
    stored = _store_unchecked(db, agent_id, _trace())

    def unreadable(**_kwargs: object) -> None:
        raise RuntimeError("anything at all")

    monkeypatch.setattr(crud, "get_trace", unreadable)
    first = client.post(f"{API}/agents/{agent_id}/checks/run", cookies=auth_cookies)
    monkeypatch.undo()
    second = client.post(f"{API}/agents/{agent_id}/checks/run", cookies=auth_cookies)

    assert first.json() == {"checked": 0, "remaining": 0}
    assert second.json() == {"checked": 0, "remaining": 0}
    row = db.get(CallCheck, (stored, CHECK))
    assert row is not None
    assert row.outcome == "broke"
    assert _status(client, auth_cookies, str(stored)) == "unchecked"
