"""`read_calls`: many calls in full for an assistant. Every call here is invented."""

import json
import uuid
from collections.abc import Generator
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core import encryption
from app.core.config import settings
from app.models import Agent, Call
from app.services import call_read
from app.services.checks.engine import check_call_safely
from app.services.mappings.retell import retell_call_to_trace
from app.tests.api.routes.test_call_screen import (
    BOOKING,
    CALLER,
    ISSUER,
    MCP_URL,
    NOW_MS,
    _agent,
    _headers,
    _signed_in,
)
from app.tests.utils.retell_payloads import invocation, result, retell_call, speech

API = settings.API_V1_STR


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    yield
    encryption._fernet.cache_clear()


def _call(
    db: Session,
    agent: Agent,
    *,
    minutes_ago: int,
    said: str = "I need a repair",
    version: int = 88,
) -> Call:
    """A finished call that started `minutes_ago`: three turns and one tool call."""
    payload = retell_call(
        f"call_{uuid.uuid4().hex[:10]}",
        agent_id=agent.platform_agent_id or "",
        timeline=[
            speech("agent", "Thank you for calling", 0.5),
            speech("user", said, 3.0),
            invocation(
                "t1", "schedule_appointment", json.dumps(BOOKING), time_sec=10.0
            ),
            result(
                "t1",
                '{"status": "booked", "secret": "s3"}',
                successful=True,
                time_sec=10.8,
            ),
            speech("agent", "You are all set", 12.0),
        ],
        start_ms=NOW_MS - minutes_ago * 60_000,
        duration_ms=73_000,
        from_number=CALLER,
        agent_version=version,
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
    return stored.call


def _read(client: TestClient, user: Any, **params: Any) -> dict[str, Any]:
    r = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/calls/read",
        params=params,
        headers=_headers(user),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_a_page_answers_each_call_in_full_and_compact(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent = _agent(db, user, "key_invented_read")
    older = _call(db, agent, minutes_ago=30)
    newer = _call(db, agent, minutes_ago=10)

    answer = _read(client, user)

    calls = answer["data"]["calls"]
    assert [c["id"] for c in calls] == [str(newer.id), str(older.id)]
    assert answer["data"]["matching"] == 2
    assert answer["next_cursor"] is None
    call = calls[0]
    assert call["agent_name"] == "Front desk"
    assert call["caller_last_four"] == "4821"
    assert call["version"] == "88"
    assert call["duration_seconds"] == 73
    assert call["conversation"] == [
        {"speaker": "agent", "text": "Thank you for calling"},
        {"speaker": "caller", "text": "I need a repair"},
        {
            "tool": "schedule_appointment",
            "status": "ok",
            "arguments": {
                "full_name": "Sam Example",
                "streetAddress": "1 Invented Road",
                "postalCode": "00000",
                "startTime": "2026-10-23T12:00:00-04:00",
                "api_key": "••••",
                "nested": '{"note": "kept", "token": "••••"}',
            },
            "result": {"status": "booked", "secret": "••••"},
        },
        {"speaker": "agent", "text": "You are all set"},
    ]
    # Compact: nothing an analysis does not need, and never the full number or a
    # secret.
    text = json.dumps(answer)
    for absent in (
        "at_seconds",
        "duration_ms",
        "recording",
        CALLER,
        "sk-invented",
        "tok-invented",
    ):
        assert absent not in text
    assert any("your own analysis" in rule for rule in answer["rules"])


def test_the_same_filters_as_list_calls_narrow_it(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent = _agent(db, user, "key_invented_read_a")
    other = _agent(db, user, "key_invented_read_b")
    on_88 = _call(db, agent, minutes_ago=10)
    on_89 = _call(db, agent, minutes_ago=20, version=89)
    others = _call(db, other, minutes_ago=30)
    everything = {str(on_88.id), str(on_89.id), str(others.id)}

    def ids(**params: Any) -> set[str]:
        read = {c["id"] for c in _read(client, user, **params)["data"]["calls"]}
        listed = client.get(
            f"{API}/mcp/workspaces/{user.company_id}/calls",
            params=params,
            headers=_headers(user),
        ).json()
        # Whatever `list_calls` lists for a filter, `read_calls` reads.
        assert read == {c["id"] for c in listed["data"]["calls"]}
        return read

    assert ids() == everything
    assert ids(agent_id=str(other.id)) == {str(others.id)}
    assert ids(version="89") == {str(on_89.id)}
    assert ids(query="4821") == everything
    assert ids(query="0000") == set()
    ids(result="failed")
    ids(result="clean")
    assert ids(period="7d") == everything


def test_a_page_stops_at_the_size_limit_and_the_cursor_goes_on_without_a_gap(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, _ = _signed_in(client, db)
    agent = _agent(db, user, "key_invented_read_c")
    calls = [_call(db, agent, minutes_ago=10 * (i + 1)) for i in range(5)]
    one = len(json.dumps(_read(client, user, limit=1)["data"]["calls"][0]))
    # Room for two calls and a part of a third.
    monkeypatch.setattr(call_read, "MAX_BYTES", int(one * 2.5))

    seen: list[str] = []
    pages = 0
    cursor = None
    while True:
        answer = _read(client, user, **({"cursor": cursor} if cursor else {}))
        page = [c["id"] for c in answer["data"]["calls"]]
        assert 1 <= len(page) <= 2
        seen += page
        pages += 1
        cursor = answer["next_cursor"]
        if cursor is None:
            break
        assert any("next_cursor" in step for step in answer["next_steps"])

    assert seen == [str(c.id) for c in calls]
    assert pages == 3
    assert answer["data"]["matching"] == 5


def test_a_call_larger_than_the_limit_comes_alone_and_whole(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, _ = _signed_in(client, db)
    agent = _agent(db, user, "key_invented_read_d")
    small = _call(db, agent, minutes_ago=30)
    long_story = "and then " * 400
    large = _call(db, agent, minutes_ago=10, said=long_story)
    monkeypatch.setattr(call_read, "MAX_BYTES", 1000)

    first = _read(client, user)
    second = _read(client, user, cursor=first["next_cursor"])

    assert [c["id"] for c in first["data"]["calls"]] == [str(large.id)]
    assert first["data"]["calls"][0]["conversation"][1]["text"] == long_story
    assert [c["id"] for c in second["data"]["calls"]] == [str(small.id)]
    assert second["next_cursor"] is None


def test_a_transcript_in_another_script_counts_for_what_it_costs(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, _ = _signed_in(client, db)
    agent = _agent(db, user, "key_invented_read_h")
    # The same number of characters, in English and in Chinese.
    for minutes_ago in (10, 20, 30):
        _call(db, agent, minutes_ago=minutes_ago, said="a" * 300)
    english = len(_read(client, user)["data"]["calls"])
    other, _ = _signed_in(client, db)
    theirs = _agent(db, other, "key_invented_read_i")
    for minutes_ago in (10, 20, 30):
        _call(db, theirs, minutes_ago=minutes_ago, said="修" * 300)
    one = len(json.dumps(_read(client, user, limit=1)["data"]["calls"][0]))
    # Room for all three English calls, counted in characters or in bytes.
    monkeypatch.setattr(call_read, "MAX_BYTES", one * 3 + 50)

    assert english == 3
    assert len(_read(client, user)["data"]["calls"]) == 3
    # Three times the bytes for the same characters: fewer calls fit.
    assert len(_read(client, other)["data"]["calls"]) < 3


def test_the_count_is_capped_and_nothing_matching_says_so(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent = _agent(db, user, "key_invented_read_e")
    path = f"{API}/mcp/workspaces/{user.company_id}/calls/read"

    empty = _read(client, user)
    too_many = client.get(path, params={"limit": 51}, headers=_headers(user))
    _call(db, agent, minutes_ago=10)
    _call(db, agent, minutes_ago=20)
    one = _read(client, user, limit=1)

    assert empty["data"] == {"calls": [], "matching": 0}
    assert any("No call matches" in step for step in empty["next_steps"])
    assert too_many.status_code == 422
    assert len(one["data"]["calls"]) == 1
    assert one["next_cursor"] is not None


def test_another_workspaces_calls_are_never_read(
    client: TestClient, db: Session
) -> None:
    owner, _ = _signed_in(client, db)
    outsider, _ = _signed_in(client, db)
    _call(db, _agent(db, owner, "key_invented_read_f"), minutes_ago=10)

    theirs = client.get(
        f"{API}/mcp/workspaces/{owner.company_id}/calls/read",
        headers=_headers(outsider),
    )
    own = _read(client, outsider)
    nobody = client.get(f"{API}/mcp/workspaces/{owner.company_id}/calls/read")

    assert theirs.status_code == 404
    assert own["data"]["calls"] == []
    assert nobody.status_code == 401


def test_the_single_call_route_still_answers_by_id(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    call = _call(db, _agent(db, user, "key_invented_read_g"), minutes_ago=10)

    one = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/calls/{call.id}",
        headers=_headers(user),
    )

    assert one.status_code == 200, one.text
    assert one.json()["data"]["id"] == str(call.id)
