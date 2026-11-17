"""Marking spec rules critical through MCP, and the marks carried into later spec
versions, on invented agents and calls (plan `plans/2026-11-17-critical-rules.md`)."""

from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.models import Agent, Spec, User
from app.models.enums import SpecOrigin
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_mcp_clarifications import QUESTION, _answer, _raise
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _booking,
    _headers,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_spec_api import (
    RULES,
    _catalogue,
    _read,
    _setup,
    _url,
    _write,
)


def _mark(
    client: TestClient,
    user: User,
    agent: Agent,
    critical: list[str] | None = None,
    not_critical: list[str] | None = None,
) -> Any:
    return client.post(
        f"{_url(user, agent)}/critical",
        headers=_headers(user),
        json={"critical": critical or [], "not_critical": not_critical or []},
    )


def _marks(data: dict[str, Any]) -> dict[str, bool]:
    return {r["text"]: r["critical"] for g in data["groups"] for r in g["rules"]}


def _keys(data: dict[str, Any]) -> dict[str, str]:
    return {r["text"]: r["key"] for g in data["groups"] for r in g["rules"]}


def _origins(db: Session, agent: Agent) -> list[SpecOrigin]:
    return [
        s.origin
        for s in db.exec(
            select(Spec).where(Spec.agent_id == agent.id).order_by(col(Spec.version))
        ).all()
    ]


BOOKING, PRICE = RULES[0]["text"], RULES[1]["text"]


def test_write_spec_stores_marks_and_kept_rules_keep_theirs(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)

    first = _write(client, user, agent, [RULES[0], RULES[1] | {"critical": True}])

    assert first.status_code == 200, first.text
    body = first.json()
    assert _marks(body["data"]) == {BOOKING: False, PRICE: True}
    assert body["data"]["counts"]["critical"] == 1
    assert any("1 of the spec's 2 rules is critical" in s for s in body["next_steps"])
    keys = _keys(body["data"])

    # Passed again without `critical`, a kept rule keeps its mark; given, it changes.
    again = _write(
        client,
        user,
        agent,
        [
            RULES[0] | {"key": keys[BOOKING], "critical": True},
            RULES[1] | {"key": keys[PRICE]},
        ],
    ).json()["data"]
    assert _marks(again) == {BOOKING: True, PRICE: True}
    cleared = _write(
        client, user, agent, [RULES[0] | {"key": keys[BOOKING], "critical": False}]
    ).json()["data"]
    assert _marks(cleared) == {BOOKING: False}


def test_write_spec_without_critical_rules_points_at_marking(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)

    body = _write(client, user, agent, RULES).json()

    assert body["data"]["counts"]["critical"] == 0
    assert any("mark_critical_rules" in s for s in body["next_steps"])
    assert any("When unsure, not critical" in rule for rule in body["rules"])


def test_mark_critical_rules_makes_one_marked_version(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)
    keys = _keys(
        _write(client, user, agent, [RULES[0] | {"critical": True}, RULES[1]]).json()[
            "data"
        ]
    )

    r = _mark(client, user, agent, critical=[keys[PRICE]], not_critical=[keys[BOOKING]])

    assert r.status_code == 200, r.text
    body = r.json()
    data = body["data"]
    assert _marks(data) == {BOOKING: False, PRICE: True}
    assert _keys(data) == keys
    assert (data["spec"]["version"], data["spec"]["origin"]) == (2, "marked")
    assert data["spec"]["assistant"] == "your assistant"
    # Marking changes nothing the spec says: it stays current.
    assert data["state"] == "current"
    assert body["next_steps"][0] == "2 rules changed; spec version 2 has them."
    # The earlier version keeps the marks it had.
    assert _marks(_read(client, user, agent, version=1).json()["data"]) == {
        BOOKING: True,
        PRICE: False,
    }


def test_marking_what_is_already_marked_makes_no_version(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)
    keys = _keys(
        _write(client, user, agent, [RULES[0], RULES[1] | {"critical": True}]).json()[
            "data"
        ]
    )

    r = _mark(client, user, agent, critical=[keys[PRICE]], not_critical=[keys[BOOKING]])

    assert r.status_code == 200, r.text
    assert r.json()["data"]["spec"]["version"] == 1
    assert "no version was made" in r.json()["next_steps"][0]
    assert _origins(db, agent) == [SpecOrigin.WRITTEN]


def test_unknown_keys_and_keys_in_both_lists_are_refused(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)
    keys = _keys(_write(client, user, agent, RULES).json()["data"])

    r = _mark(
        client,
        user,
        agent,
        critical=[keys[PRICE], "nope"],
        not_critical=[keys[PRICE]],
    )

    assert r.status_code == 422, r.text
    steps = r.json()["detail"]["next_steps"]
    assert any(f"'{keys[PRICE]}' is in both lists" in s for s in steps)
    assert any("'nope' is not a rule of spec version 1" in s for s in steps)
    assert _origins(db, agent) == [SpecOrigin.WRITTEN]
    assert _mark(client, user, agent).status_code == 422


def test_an_agent_without_a_spec_cannot_mark(client: TestClient, db: Session) -> None:
    user, agent = _setup(db)

    r = _mark(client, user, agent, critical=["k1"])

    assert r.status_code == 422, r.text
    assert r.json()["detail"]["error"] == "The agent has no spec yet"


def test_another_workspace_cannot_mark(client: TestClient, db: Session) -> None:
    user, agent = _setup(db)
    keys = _keys(_write(client, user, agent, RULES).json()["data"])
    other = _person(db)

    r = client.post(
        f"{_url(other, agent)}/critical",
        headers=_headers(other),
        json={"critical": [keys[PRICE]]},
    )

    assert r.status_code == 404, r.text
    assert _origins(db, agent) == [SpecOrigin.WRITTEN]


def test_an_adopted_version_carries_the_marks(client: TestClient, db: Session) -> None:
    user, agent = _setup(db)
    _write(client, user, agent, [RULES[0], RULES[1] | {"critical": True}])
    _catalogue(db, agent, "8")

    _call(db, agent, _booking(1, FULL), days_ago=0, version=8)

    data = _read(client, user, agent).json()["data"]
    assert data["spec"]["origin"] == "adopted"
    assert _marks(data) == {BOOKING: False, PRICE: True}


def test_answers_carry_marks_and_a_replacing_answer_keeps_the_mark(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)
    keys = _keys(
        _write(client, user, agent, [RULES[0] | {"critical": True}, RULES[1]]).json()[
            "data"
        ]
    )
    replacing, new = _raise(
        client,
        user,
        agent,
        QUESTION | {"replaces_key": keys[BOOKING]},
        QUESTION | {"question": "May the agent move an appointment to another day?"},
    ).json()["data"]

    answered = _answer(client, user, (replacing["id"], "c"), (new["id"], "a"))

    assert answered.status_code == 200, answered.text
    data = _read(client, user, agent).json()["data"]
    assert data["spec"]["origin"] == "answered"
    assert _marks(data) == {
        "Never change an existing appointment": True,
        "The agent may change an existing appointment": False,
        PRICE: False,
    }
    assert _keys(data)["Never change an existing appointment"] == keys[BOOKING]

    # The person's answers can be marked like any rule, and a later write keeps them.
    marked = _mark(
        client,
        user,
        agent,
        critical=[_keys(data)["The agent may change an existing appointment"]],
    ).json()["data"]
    assert _marks(marked)["The agent may change an existing appointment"] is True
    rewritten = _write(client, user, agent, [RULES[1] | {"key": keys[PRICE]}]).json()[
        "data"
    ]
    assert _marks(rewritten) == {
        "Never change an existing appointment": True,
        "The agent may change an existing appointment": True,
        PRICE: False,
    }
