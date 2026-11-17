"""Writing, listing and grouping scenarios through MCP, their links to spec rules, and the
Scenarios task on Work, on invented agents and calls (plan
`plans/2026-11-17-scenarios.md`)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Agent, Company, Spec, TestCase, User
from app.models.enums import TestCaseStatus
from app.models.eval_config import EvalConfig, EvalConfigMember
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _headers,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_spec_api import (
    API,
    RULES,
    _catalogue,
    _read,
    _setup,
    _write,
)

BOOKING, PRICE = RULES[0]["text"], RULES[1]["text"]


def _base(user: User, agent: Agent) -> str:
    return f"{API}/mcp/workspaces/{user.company_id}/agents/{agent.id}"


def _scenarios(client: TestClient, user: User, agent: Agent, *items: Any) -> Any:
    return client.post(
        f"{_base(user, agent)}/scenarios",
        headers=_headers(user),
        json={"scenarios": list(items)},
    )


def _list(client: TestClient, user: User, agent: Agent, **params: Any) -> Any:
    return client.get(
        f"{_base(user, agent)}/scenarios", headers=_headers(user), params=params
    )


def _set(
    client: TestClient, user: User, agent: Agent, name: str, ids: list[str]
) -> Any:
    return client.post(
        f"{_base(user, agent)}/scenario-sets",
        headers=_headers(user),
        json={"name": name, "scenario_ids": ids},
    )


def _keys(data: dict[str, Any]) -> dict[str, str]:
    return {r["text"]: r["key"] for g in data["groups"] for r in g["rules"]}


def _ready(db: Session, client: TestClient) -> tuple[User, Agent, dict[str, str]]:
    """An agent whose spec has a critical price rule and a plain booking rule."""
    user, agent = _setup(db)
    data = _write(client, user, agent, [RULES[0], RULES[1] | {"critical": True}]).json()
    return user, agent, _keys(data["data"])


def _price(keys: dict[str, str], **extra: Any) -> dict[str, Any]:
    return {
        "name": "Price pushback",
        "description": "The caller argues about the renewal price",
        "caller": "A patient booking a cleaning",
        "caller_goal": "Find out what the cleaning costs",
        "caller_behaviour": "Insists on a number",
        "caller_knows": {"date_of_birth": "1990-01-01"},
        "agent_variables": {"clinic_hours": "9 to 5"},
        "first_turn": "agent",
        "first_message": "Hello, dental clinic.",
        "fake_tool_results": [
            {
                "tool": "check_slot",
                "arguments": {"date": None},
                "result": {"available": True},
            }
        ],
        "rules": [keys[PRICE]],
        **extra,
    }


def test_write_and_list_a_scenario_with_its_rules(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)

    r = _scenarios(client, user, agent, _price(keys))

    assert r.status_code == 200, r.text
    body = r.json()
    written = body["data"]["scenarios"][0]
    assert written["caller_goal"] == "Find out what the cleaning costs"
    assert written["caller_knows"] == {"date_of_birth": "1990-01-01"}
    assert written["agent_variables"] == {"clinic_hours": "9 to 5"}
    assert written["first_turn"] == "agent"
    assert written["fake_tool_results"] == [
        {
            "tool": "check_slot",
            "arguments": {"date": None},
            "result": {"available": True},
        }
    ]
    assert written["rules"] == [
        {"key": keys[PRICE], "text": PRICE, "critical": True, "gone": False}
    ]
    assert body["guide"] == "connexity://guides/scenarios"
    assert any("write_scenario_set" in s for s in body["next_steps"])
    stored = db.get(TestCase, uuid.UUID(written["id"]))
    assert stored is not None
    assert stored.persona_context == "A patient booking a cleaning"
    assert stored.expected_outcomes is None

    listed = _list(client, user, agent).json()["data"]
    assert [s["name"] for s in listed["data"]] == ["Price pushback"]
    assert listed["counts"] == {
        "scenarios": 1,
        "rules": 2,
        "rules_listed": 1,
        "critical_unlisted": 0,
        "listing_gone_rules": 0,
    }
    assert [r["key"] for r in listed["unlisted_rules"]] == [keys[BOOKING]]
    spec = _read(client, user, agent).json()["data"]
    counts = {r["text"]: r["scenarios"] for g in spec["groups"] for r in g["rules"]}
    assert counts == {BOOKING: 0, PRICE: 1}


def test_critical_rules_without_scenarios_are_named_first(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)

    body = _scenarios(
        client, user, agent, _price(keys, rules=[keys[BOOKING]], name="Booking")
    ).json()

    assert any(
        f"1 critical rule still has no scenario: '{keys[PRICE]}'" in s
        for s in body["next_steps"]
    )
    listed = _list(client, user, agent).json()["data"]
    assert listed["counts"]["critical_unlisted"] == 1
    assert listed["unlisted_rules"][0] == {
        "key": keys[PRICE],
        "text": PRICE,
        "critical": True,
        "gone": False,
    }
    # The spec's own next steps point at writing them.
    again = _write(
        client,
        user,
        agent,
        [
            RULES[0] | {"key": keys[BOOKING]},
            RULES[1] | {"key": keys[PRICE]},
        ],
    ).json()
    assert any("write_scenarios" in s and keys[PRICE] in s for s in again["next_steps"])


def test_every_problem_is_refused_and_nothing_is_stored(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    other_user, other_agent = _setup(db)
    foreign_call = _call(db, other_agent, _booking(1, FULL), days_ago=1, version=7)

    r = _scenarios(
        client,
        user,
        agent,
        _price(keys, rules=[]),
        _price(keys, rules=["nope"], name=""),
        _price(keys, fake_tool_results=[{"tool": " "}]),
        _price(keys, from_call_id=str(foreign_call)),
        {"id": str(uuid.uuid4()), "archive": True},
        {"archive": True},
    )

    assert r.status_code == 422, r.text
    steps = " ".join(r.json()["detail"]["next_steps"])
    assert "Scenario 1: list the spec rules" in steps
    assert "Scenario 2: the name is empty" in steps
    assert "rule 'nope' is not in the agent's latest spec" in steps
    assert "Scenario 3: fake tool result 1 has no tool name" in steps
    assert "Scenario 4: call" in steps
    assert "Scenario 5: id" in steps
    assert "Scenario 6: give the id" in steps
    assert db.exec(select(TestCase).where(TestCase.agent_id == agent.id)).all() == []


def test_an_agent_without_a_spec_and_another_workspace_are_refused(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)
    r = _scenarios(client, user, agent, {"name": "x", "rules": ["k"]})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["error"] == "The agent has no spec yet"

    _, _, keys = _ready(db, client)
    other = _person(db)
    r = client.post(
        f"{API}/mcp/workspaces/{other.company_id}/agents/{agent.id}/scenarios",
        headers=_headers(other),
        json={"scenarios": [_price(keys)]},
    )
    assert r.status_code == 404, r.text


def test_replace_by_id_archive_and_sets(client: TestClient, db: Session) -> None:
    user, agent, keys = _ready(db, client)
    first, second = _scenarios(
        client,
        user,
        agent,
        _price(keys),
        _price(keys, name="Booking", rules=[keys[BOOKING], keys[PRICE]]),
    ).json()["data"]["scenarios"]

    made = _set(client, user, agent, "smoke", [second["id"], first["id"]])
    assert made.status_code == 200, made.text
    assert made.json()["data"]["scenario_ids"] == [second["id"], first["id"]]

    replaced = _scenarios(
        client,
        user,
        agent,
        _price(keys, id=first["id"], name="Price, calmer", caller_behaviour=None),
    ).json()["data"]["scenarios"][0]
    assert (replaced["id"], replaced["name"]) == (first["id"], "Price, calmer")
    assert replaced["caller_behaviour"] is None

    listed = _list(client, user, agent, set="smoke").json()["data"]
    assert [s["name"] for s in listed["data"]] == ["Price, calmer", "Booking"]
    assert all(s["sets"] == ["smoke"] for s in listed["data"])
    by_rule = _list(client, user, agent, rule_key=keys[BOOKING]).json()["data"]
    assert [s["name"] for s in by_rule["data"]] == ["Booking"]

    archived = _scenarios(client, user, agent, {"id": second["id"], "archive": True})
    assert archived.json()["data"]["archived"] == 1
    stored = db.get(TestCase, uuid.UUID(second["id"]))
    assert stored is not None and stored.status is TestCaseStatus.ARCHIVED
    listed = _list(client, user, agent).json()["data"]
    assert [s["name"] for s in listed["data"]] == ["Price, calmer"]
    assert listed["sets"][0]["scenario_ids"] == [first["id"]]

    # A set refuses scenarios it cannot hold, and an empty list archives it.
    refused = _set(client, user, agent, "smoke", [second["id"]])
    assert refused.status_code == 422, refused.text
    assert _set(client, user, agent, "smoke", []).json()["data"] is None
    config = db.exec(select(EvalConfig).where(EvalConfig.agent_id == agent.id)).one()
    assert config.deleted_at is not None
    assert (
        db.exec(
            select(EvalConfigMember).where(EvalConfigMember.eval_config_id == config.id)
        ).all()
        == []
    )
    assert _list(client, user, agent, set="smoke").status_code == 404
    assert _set(client, user, agent, "nothing", []).status_code == 422


def test_listing_pages(client: TestClient, db: Session) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(
        client, user, agent, *[_price(keys, name=f"Scenario {n}") for n in range(3)]
    )

    first = _list(client, user, agent, limit=2).json()
    assert len(first["data"]["data"]) == 2
    cursor = first["data"]["next_cursor"]
    assert cursor
    rest = _list(client, user, agent, limit=2, cursor=cursor).json()["data"]
    assert [s["name"] for s in rest["data"]] == ["Scenario 2"]
    assert rest["next_cursor"] is None


def test_a_dropped_rule_is_reported_and_kept_rules_stay_linked(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(
        client,
        user,
        agent,
        _price(keys, name="Both", rules=[keys[BOOKING], keys[PRICE]]),
    )

    # A new spec version keeps the price rule and drops the booking rule.
    _write(client, user, agent, [RULES[1] | {"key": keys[PRICE]}])

    body = _list(client, user, agent).json()
    rules = body["data"]["data"][0]["rules"]
    assert rules == [
        {"key": keys[BOOKING], "text": None, "critical": False, "gone": True},
        {"key": keys[PRICE], "text": PRICE, "critical": True, "gone": False},
    ]
    assert body["data"]["counts"]["listing_gone_rules"] == 1
    assert any("no longer has" in s for s in body["next_steps"])


def _tasks(client: TestClient, user: User) -> list[dict[str, Any]]:
    return client.get(
        f"{API}/mcp/workspaces/{user.company_id}/tasks",
        headers=_headers(user),
        params={"limit": 100},
    ).json()["data"]["tasks"]


def test_the_scenarios_task_waits_for_the_spec_and_leaves_when_every_rule_is_listed(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    key = f"scenarios:{agent.id}"
    # Setup is done: the first scan has finished, so each agent has its own tasks.
    now = datetime.now(UTC)
    agent.scan_done_at = now
    company = db.get(Company, user.company_id)
    assert company is not None
    company.first_scan_done_at = now
    db.add(agent)
    db.add(company)
    db.commit()

    task = next(t for t in _tasks(client, user) if t["key"] == key)
    assert (task["kind"], task["title"]) == (
        "tests",
        "Write scenarios for 2 rules on Front desk",
    )
    assert task["blocked_by"] == []

    # A newer agent version: the spec needs review, and its task blocks the scenarios.
    _catalogue(db, agent, "8")
    _call(db, agent, _booking(1, FULL), days_ago=0, version=8)
    assert db.exec(select(Spec).where(Spec.agent_id == agent.id)).all()
    tasks = {t["key"]: t for t in _tasks(client, user)}
    assert [b["key"] for b in tasks[key]["blocked_by"]] == [f"spec:{agent.id}"]

    _scenarios(
        client,
        user,
        agent,
        _price(keys, name="Both", rules=[keys[BOOKING], keys[PRICE]]),
    )
    assert key not in {t["key"] for t in _tasks(client, user)}
