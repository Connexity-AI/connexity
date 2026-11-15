"""Latency from turns, the agent page's Overview, latency on the Agents list and
`get_agent`, on invented calls (plan `plans/2026-11-14-agent-page.md`)."""

import time
import uuid
from datetime import datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.crud.latency import call_latency, reply_gaps
from app.models import Agent, Call
from app.models.call import CallComponent
from app.models.enums import Speaker
from app.services.checks.engine import check_call_safely
from app.services.mappings.retell import retell_call_to_trace
from app.tests.api.routes.test_issues_list import _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    _agent,
    _headers,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_spec_api import _catalogue
from app.tests.utils.retell_payloads import invocation, result, retell_call, speech

API = settings.API_V1_STR
DAY_MS = 86_400_000


def test_reply_gaps_skip_overlaps_and_unanswered_turns() -> None:
    caller, agent = Speaker.CALLER, Speaker.AGENT
    turns: list[tuple[Speaker | None, int | None, int | None]] = [
        (agent, 0, 1000),
        (caller, 1500, 2000),
        (agent, 3200, 4000),  # 1.2 s after the caller
        (caller, 4500, 6000),
        (agent, 5800, 7000),  # starts before the caller finishes: not a gap
        (caller, 7500, 8000),  # never answered
    ]

    assert reply_gaps(turns) == [1200]
    # Someone else speaks after a transfer: the agent's next turn is not a reply gap.
    transferred: list[tuple[Speaker | None, int | None, int | None]] = [
        (caller, 0, 1000),
        (Speaker.OTHER, 2000, 20000),
        (agent, 21000, 22000),
    ]
    assert reply_gaps(transferred) == []
    assert call_latency(turns) == 1.2
    assert call_latency([(agent, 0, 1000)]) is None


def _call(
    db: Session,
    agent: Agent,
    *,
    gap: float,
    days_ago: float = 1,
    version: int = 7,
) -> uuid.UUID:
    """A call where the agent answers each caller turn ``gap`` seconds after it ends."""
    timeline: list[dict[str, Any]] = [speech("agent", "Hello", 0.5)]
    at = 2.0
    for _ in range(3):
        timeline.append(speech("user", "Yes", at))
        timeline.append(speech("agent", "Okay", at + 0.3 + gap))
        at += 0.3 + gap + 2
    timeline += [
        invocation("t1", "check_slots", "{}", time_sec=at),
        result("t1", "{}", successful=True, time_sec=at + 0.5),
    ]
    payload = retell_call(
        f"call_{uuid.uuid4().hex[:8]}",
        agent_id=agent.platform_agent_id or "",
        timeline=timeline,
        start_ms=int(time.time() * 1000 - days_ago * DAY_MS),
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
    return stored.call.id


def test_the_agent_page_answers_the_overview(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, "7")
    _catalogue(db, agent, "8")
    _call(db, agent, gap=1.0, days_ago=3, version=7)
    _call(db, agent, gap=2.0, days_ago=1, version=8)
    _call(db, agent, gap=1.0, days_ago=60, version=7)

    r = client.get(f"{API}/agents/{agent.id}/page", cookies=cookies)

    assert r.status_code == 200, r.text
    page = r.json()
    assert (page["name"], page["platform"], page["type"]) == (
        "Front desk",
        "retell",
        "single_prompt",
    )
    assert page["live_version"] == "8"
    assert page["live_since"] is not None
    assert (page["calls"], page["latency_calls"]) == (2, 2)
    assert page["latency_seconds"] == 1.5
    assert len(page["latency_days"]) == 30
    assert page["latency_peak"] == 2.0
    assert [m["label"] for m in page["version_marks"]] == ["Version 8"]
    assert page["spec"] == "none"
    assert page["systems"] == []
    week = client.get(
        f"{API}/agents/{agent.id}/page", cookies=cookies, params={"period": "7d"}
    ).json()
    assert len(week["latency_days"]) == 7


def test_the_agents_list_has_latency(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    _agent(db, user, "Quiet line")
    _call(db, agent, gap=1.0)
    _call(db, agent, gap=3.0)

    rows = client.get(f"{API}/agents/list", cookies=cookies).json()["data"]

    assert {r["name"]: r["latency_seconds"] for r in rows} == {
        "Front desk": 2.0,
        "Quiet line": None,
    }


def test_another_workspace_and_unknown_agents_are_not_found(
    client: TestClient, db: Session
) -> None:
    _, cookies = _signed_in(client, db)
    other = _person(db)
    elsewhere = _agent(db, other, "Elsewhere")

    assert (
        client.get(f"{API}/agents/{elsewhere.id}/page", cookies=cookies).status_code
        == 404
    )
    assert (
        client.get(f"{API}/agents/{uuid.uuid4()}/page", cookies=cookies).status_code
        == 404
    )


def test_get_agent_and_list_agents_through_mcp(client: TestClient, db: Session) -> None:
    user = _person(db)
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, "7")
    _call(db, agent, gap=1.0)
    base = f"{API}/mcp/workspaces/{user.company_id}/agents"

    one = client.get(f"{base}/{agent.id}", headers=_headers(user))
    listed = client.get(base, headers=_headers(user)).json()

    assert one.status_code == 200, one.text
    body = one.json()
    assert (body["data"]["latency_seconds"], body["data"]["calls"]) == (1.0, 1)
    assert any("basic measure" in rule for rule in body["rules"])
    assert any("write_spec" in s for s in body["next_steps"])
    assert listed["data"][0]["latency_seconds"] == 1.0
    stranger = client.get(f"{base}/{agent.id}", headers=_headers(_person(db)))
    assert stranger.status_code == 404


def test_systems_are_the_workflows_its_calls_ran(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    older = _call(db, agent, gap=1.0, days_ago=3)
    newer = _call(db, agent, gap=1.0, days_ago=1)
    for call_id, version in ((older, "6"), (newer, "7")):
        db.add(
            CallComponent(
                company_id=agent.company_id,
                call_id=call_id,
                seq=99,
                kind="skill",
                name="quote-lookup",
                ref="wf_invented",
                version=version,
            )
        )
    db.commit()

    page = client.get(f"{API}/agents/{agent.id}/page", cookies=cookies).json()

    assert page["systems"] == [
        {"kind": "n8n workflow", "name": "quote-lookup", "version": "7"}
    ]


def test_live_since_counts_from_the_return_to_an_older_version(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    _call(db, agent, gap=1.0, days_ago=20, version=7)
    _call(db, agent, gap=1.0, days_ago=10, version=8)
    back = _call(db, agent, gap=1.0, days_ago=4, version=7)
    _call(db, agent, gap=1.0, days_ago=1, version=7)
    returned = db.get(Call, back)
    assert returned is not None

    page = client.get(f"{API}/agents/{agent.id}/page", cookies=cookies).json()

    assert page["live_version"] == "7"
    assert datetime.fromisoformat(page["live_since"]).replace(
        tzinfo=None
    ) == returned.started_at.replace(tzinfo=None)
