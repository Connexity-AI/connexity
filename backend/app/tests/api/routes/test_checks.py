"""Checks on arrival, findings on the call, settings and their decision records."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Call, DecisionRecord, Finding
from app.models.enums import CheckMode
from app.services.checks import engine
from app.services.checks.base import CheckInput, Raised, RuleCheck
from app.tests.utils.utils import extract_cookies, random_email, random_lower_string

API = settings.API_V1_STR
CHECK = "tool_call_failed"


def _agent(client: TestClient, cookies: dict[str, str]) -> str:
    r = client.post(
        f"{API}/agents/",
        json={
            "name": f"agent-{uuid.uuid4().hex[:6]}",
            "endpoint_url": "http://example.com/agent",
        },
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def token(client: TestClient, auth_cookies: dict[str, str]) -> str:
    r = client.post(
        f"{API}/ingest-tokens/", json={"name": "checks"}, cookies=auth_cookies
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _other_company(client: TestClient) -> dict[str, str]:
    email, password = random_email(), random_lower_string()
    r = client.post(f"{API}/users/signup", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    r = client.post(
        f"{API}/login/access-token", data={"username": email, "password": password}
    )
    assert r.status_code == 200, r.text
    return extract_cookies(r)


def _trace(
    *,
    tool_status: str = "error",
    external_id: str | None = None,
    started_at: datetime | None = None,
) -> dict[str, Any]:
    """An invented call: the caller asks, the agent calls one tool, the agent answers."""
    return {
        "provider": "invented",
        "external_id": external_id or f"call-{uuid.uuid4().hex[:10]}",
        "started_at": (started_at or datetime.now(UTC)).isoformat(),
        "events": [
            {"id": "u1", "type": "utterance", "speaker": "caller", "text": "A table?"},
            {
                "id": "t1",
                "type": "tool_call",
                "name": "find_table",
                "status": tool_status,
            },
            {"id": "u2", "type": "utterance", "speaker": "agent", "text": "One moment"},
        ],
    }


def _send(client: TestClient, token: str, agent_id: str, trace: dict[str, Any]) -> str:
    r = client.post(
        f"{API}/ingest/traces",
        json={"agent_id": agent_id, "trace": trace},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()["call_id"]


def _read(client: TestClient, cookies: dict[str, str], call_id: str) -> dict[str, Any]:
    r = client.get(f"{API}/calls/{call_id}/trace", cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json()


def _set(
    client: TestClient,
    cookies: dict[str, str],
    agent_id: str,
    mode: str,
    reason: str | None = None,
    check: str = CHECK,
) -> Any:
    return client.put(
        f"{API}/agents/{agent_id}/checks/{check}",
        json={"mode": mode, "reason": reason},
        cookies=cookies,
    )


# ── On arrival ─────────────────────────────────────────────────────


def test_a_failing_tool_call_is_found_when_the_call_arrives(
    client: TestClient, auth_cookies: dict[str, str], token: str, db: Session
) -> None:
    agent_id = _agent(client, auth_cookies)

    call_id = _send(client, token, agent_id, _trace())

    body = _read(client, auth_cookies, call_id)
    (finding,) = body["findings"]
    assert finding["check_type"] == CHECK
    assert finding["check_version"] == 1
    assert finding["kind"] == "rule"
    assert finding["title"] == "Tool call failed"
    assert finding["event_ids"] == ["t1"]
    assert finding["key"] == "find_table"
    assert finding["detail"] == {"status": "error"}
    assert finding["effect"] == "fails"
    assert finding["retroactive"] is False
    assert body["checked_at"] is not None

    row = db.exec(select(Finding).where(Finding.call_id == uuid.UUID(call_id))).one()
    assert str(row.agent_id) == agent_id
    call = db.get(Call, uuid.UUID(call_id))
    assert call is not None
    assert row.company_id == call.company_id


def test_a_call_whose_tool_call_succeeded_is_checked_and_has_no_finding(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)

    body = _read(
        client, auth_cookies, _send(client, token, agent_id, _trace(tool_status="ok"))
    )

    assert body["findings"] == []
    assert body["checked_at"] is not None


def test_sending_a_call_again_keeps_its_finding_and_a_fixed_trace_removes_it(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    trace = _trace()

    call_id = _send(client, token, agent_id, trace)
    (first,) = _read(client, auth_cookies, call_id)["findings"]
    assert _send(client, token, agent_id, trace) == call_id
    (second,) = _read(client, auth_cookies, call_id)["findings"]

    assert second["id"] == first["id"]
    assert second["created_at"] == first["created_at"]

    _send(
        client,
        token,
        agent_id,
        {
            **_trace(tool_status="ok"),
            **{"external_id": trace["external_id"], "started_at": trace["started_at"]},
        },
    )
    assert _read(client, auth_cookies, call_id)["findings"] == []


def test_a_call_that_started_before_the_check_existed_gets_a_retroactive_finding(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    long_ago = datetime(2020, 1, 1, tzinfo=UTC)

    call_id = _send(client, token, agent_id, _trace(started_at=long_ago))

    (finding,) = _read(client, auth_cookies, call_id)["findings"]
    assert finding["retroactive"] is True


def test_a_check_that_breaks_leaves_the_call_stored_and_unchecked(
    client: TestClient,
    auth_cookies: dict[str, str],
    token: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    agent_id = _agent(client, auth_cookies)
    trace = _trace()
    call_id = _send(client, token, agent_id, trace)

    def broken(_input: CheckInput) -> list[Raised]:
        raise RuntimeError("anything at all")

    monkeypatch.setattr(
        engine,
        "CHECKS",
        (
            RuleCheck(
                type=CHECK,
                version=1,
                title="Broken",
                description="For tests.",
                default_mode=CheckMode.FAILS,
                run=broken,
            ),
        ),
    )
    with caplog.at_level(logging.ERROR):
        assert _send(client, token, agent_id, trace) == call_id
        new_call = _send(client, token, agent_id, _trace())

    assert f"Check '{CHECK}' broke on call {call_id}" in caplog.text
    # The call already checked keeps the finding it had.
    assert len(_read(client, auth_cookies, call_id)["findings"]) == 1
    fresh = _read(client, auth_cookies, new_call)
    assert len(fresh["trace"]["events"]) == 3
    assert fresh["findings"] == []
    assert fresh["checked_at"] is None


def test_checking_again_leaves_findings_of_other_checks_alone(
    client: TestClient, auth_cookies: dict[str, str], token: str, db: Session
) -> None:
    agent_id = _agent(client, auth_cookies)
    trace = _trace()
    call_id = _send(client, token, agent_id, trace)
    (mine,) = db.exec(
        select(Finding).where(Finding.call_id == uuid.UUID(call_id))
    ).all()
    db.add(
        Finding(
            company_id=mine.company_id,
            agent_id=mine.agent_id,
            call_id=mine.call_id,
            check_type="a_check_since_removed",
            check_version=1,
            kind=mine.kind,
            event_keys=["u1"],
            effect=mine.effect,
        )
    )
    db.commit()

    _send(client, token, agent_id, trace)

    findings = _read(client, auth_cookies, call_id)["findings"]
    assert sorted(f["check_type"] for f in findings) == [
        "a_check_since_removed",
        CHECK,
    ]
    assert next(f for f in findings if f["check_type"] != CHECK)["title"] == ""


# ── Settings ───────────────────────────────────────────────────────


def test_checks_are_listed_with_their_default(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    agent_id = _agent(client, auth_cookies)

    r = client.get(f"{API}/agents/{agent_id}/checks", cookies=auth_cookies)

    assert r.status_code == 200, r.text
    (check,) = (item for item in r.json() if item["type"] == CHECK)
    assert check["title"] == "Tool call failed"
    assert check["kind"] == "rule"
    assert check["version"] == 1
    assert (check["default_mode"], check["mode"]) == ("fails", "fails")


def test_switching_a_check_off_applies_to_later_calls_of_that_agent_only(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    other_agent_id = _agent(client, auth_cookies)

    r = _set(client, auth_cookies, agent_id, "off", "The tool is being replaced")
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "off"

    later = datetime.now(UTC) + timedelta(seconds=1)
    quiet = _read(
        client,
        auth_cookies,
        _send(client, token, agent_id, _trace(started_at=later)),
    )
    loud = _read(
        client,
        auth_cookies,
        _send(client, token, other_agent_id, _trace(started_at=later)),
    )

    assert quiet["findings"] == []
    assert quiet["checked_at"] is not None
    assert len(loud["findings"]) == 1


def test_a_setting_change_is_recorded_with_who_when_what_and_why(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _agent(client, auth_cookies)
    me = client.get(f"{API}/users/me", cookies=auth_cookies).json()
    before = datetime.now(UTC)

    assert (
        _set(client, auth_cookies, agent_id, "flags", "  Too noisy  ").status_code
        == 200
    )
    assert _set(client, auth_cookies, agent_id, "fails").status_code == 200

    r = client.get(f"{API}/agents/{agent_id}/decisions", cookies=auth_cookies)
    assert r.status_code == 200, r.text
    tightened, loosened = r.json()
    assert loosened["kind"] == "check_setting"
    assert loosened["subject"] == CHECK
    assert (loosened["old_value"], loosened["new_value"]) == ("fails", "flags")
    assert loosened["reason"] == "Too noisy"
    assert loosened["decided_by"] == me["id"]
    assert loosened["decided_by_email"] == me["email"]
    assert before <= datetime.fromisoformat(loosened["created_at"]) <= datetime.now(UTC)
    # Tightening needs no reason.
    assert (tightened["old_value"], tightened["new_value"]) == ("flags", "fails")
    assert tightened["reason"] is None

    rows = db.exec(
        select(DecisionRecord).where(DecisionRecord.agent_id == uuid.UUID(agent_id))
    ).all()
    assert len(rows) == 2


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_loosening_without_a_reason_is_refused_and_records_nothing(
    client: TestClient, auth_cookies: dict[str, str], reason: str | None
) -> None:
    agent_id = _agent(client, auth_cookies)

    r = _set(client, auth_cookies, agent_id, "flags", reason)

    assert r.status_code == 422, r.text
    assert "reason is required" in r.json()["detail"]
    checks = client.get(f"{API}/agents/{agent_id}/checks", cookies=auth_cookies).json()
    assert [c["mode"] for c in checks if c["type"] == CHECK] == ["fails"]
    decisions = client.get(f"{API}/agents/{agent_id}/decisions", cookies=auth_cookies)
    assert decisions.json() == []


def test_setting_a_check_to_what_it_already_is_records_nothing(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    agent_id = _agent(client, auth_cookies)

    r = _set(client, auth_cookies, agent_id, "fails")

    assert r.status_code == 200, r.text
    decisions = client.get(f"{API}/agents/{agent_id}/decisions", cookies=auth_cookies)
    assert decisions.json() == []


def test_a_finding_keeps_its_effect_after_the_setting_changes(
    client: TestClient, auth_cookies: dict[str, str], token: str
) -> None:
    agent_id = _agent(client, auth_cookies)
    trace = _trace()
    call_id = _send(client, token, agent_id, trace)
    (before,) = _read(client, auth_cookies, call_id)["findings"]

    assert (
        _set(client, auth_cookies, agent_id, "flags", "Known, being fixed").status_code
        == 200
    )
    _send(client, token, agent_id, trace)
    (after,) = _read(client, auth_cookies, call_id)["findings"]
    later = datetime.now(UTC) + timedelta(seconds=1)
    (new,) = _read(
        client,
        auth_cookies,
        _send(client, token, agent_id, _trace(started_at=later)),
    )["findings"]

    assert before["effect"] == "fails"
    assert (after["id"], after["effect"]) == (before["id"], "fails")
    assert new["effect"] == "flags"


def test_an_unknown_check_or_mode_is_refused(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    agent_id = _agent(client, auth_cookies)

    assert (
        _set(client, auth_cookies, agent_id, "off", "x", check="nope").status_code
        == 404
    )
    assert _set(client, auth_cookies, agent_id, "sometimes", "x").status_code == 422


def test_another_company_cannot_see_or_change_an_agents_checks(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    agent_id = _agent(client, auth_cookies)
    stranger = _other_company(client)

    assert (
        client.get(f"{API}/agents/{agent_id}/checks", cookies=stranger).status_code
        == 404
    )
    assert (
        client.get(f"{API}/agents/{agent_id}/decisions", cookies=stranger).status_code
        == 404
    )
    assert _set(client, stranger, agent_id, "off", "x").status_code == 404
    assert client.get(f"{API}/agents/{agent_id}/checks").status_code == 401
