"""Raising, listing and answering clarifications through MCP, and the next steps that
point at them, on invented agents and calls (plan
`plans/2026-11-15-clarifications-mcp.md`)."""

import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import Agent, User
from app.services.spec import write_agent_spec
from app.tests.api.routes.test_issue_page import MISSING, _call, _issue
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _headers,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_spec_api import _catalogue
from app.tests.services.test_clarifications import ASSISTANT, RULES, _ready

API = settings.API_V1_STR
QUESTION: dict[str, Any] = {
    "question": "The agent changed an existing appointment on 2 calls. Is it allowed to?",
    "answers": [
        {
            "label": "Yes, always",
            "rule": "The agent may change an existing appointment",
        },
        {
            "label": "Only when the caller asks",
            "rule": "Change an existing appointment only when the caller asks for it",
        },
        {"label": "Never", "rule": "Never change an existing appointment"},
    ],
    "category": "booking",
}
DEPOSIT: dict[str, Any] = {
    "question": "Callers asked about a deposit. May the agent say one is needed?",
    "answers": [
        {"label": "Yes", "rule": "Tell callers a deposit is needed for new patients"},
        {"label": "No", "rule": "Never mention a deposit"},
    ],
    "category": "pricing_and_quotes",
    "touches": "money",
}


def _base(user: User) -> str:
    return f"{API}/mcp/workspaces/{user.company_id}"


def _raise(
    client: TestClient, user: User, agent: Agent, *questions: dict[str, Any]
) -> Any:
    return client.post(
        f"{_base(user)}/agents/{agent.id}/clarifications",
        headers=_headers(user),
        json={"questions": list(questions)},
    )


def _answer(client: TestClient, user: User, *answers: tuple[str, str]) -> Any:
    return client.post(
        f"{_base(user)}/clarifications/answers",
        headers=_headers(user),
        json={"answers": [{"clarification_id": i, "answer": a} for i, a in answers]},
    )


def test_raise_list_answer_and_read_the_spec(client: TestClient, db: Session) -> None:
    user, agent, calls = _ready(db)

    raised = _raise(
        client, user, agent, QUESTION | {"call_ids": [str(c) for c in calls]}, DEPOSIT
    )

    assert raised.status_code == 200, raised.text
    body = raised.json()
    change, deposit = body["data"]
    assert (change["calls_seen"], change["state"], change["spec_version"]) == (
        2,
        "open",
        1,
    )
    assert [a["letter"] for a in change["answers"]] == ["a", "b", "c"]
    assert change["category_name"]
    assert "answer_clarifications" in body["next_steps"][0]
    assert any("The person answers" in rule for rule in body["rules"])

    listed = client.get(f"{_base(user)}/clarifications", headers=_headers(user)).json()
    assert listed["data"]["counts"] == {
        "open": 2,
        "answered": 0,
        "parked": 0,
        "answered_this_week": 0,
    }
    assert {c["id"] for c in listed["data"]["data"]} == {change["id"], deposit["id"]}

    spec = client.get(
        f"{_base(user)}/agents/{agent.id}/spec", headers=_headers(user)
    ).json()
    assert spec["data"]["open_clarifications"] == 2
    assert any("2 questions wait" in s for s in spec["next_steps"])

    answered = _answer(client, user, (change["id"], "b"), (deposit["id"], "park"))

    assert answered.status_code == 200, answered.text
    result = answered.json()["data"]
    assert (result["answered"], result["parked"], result["open"]) == (1, 1, 0)
    assert result["specs"] == [
        {
            "agent_id": str(agent.id),
            "agent_name": "Front desk",
            "spec_version": 2,
            "rules_added": 1,
        }
    ]
    spec = client.get(
        f"{_base(user)}/agents/{agent.id}/spec", headers=_headers(user)
    ).json()
    rules = [r for g in spec["data"]["groups"] for r in g["rules"]]
    assert {r["text"] for r in rules if r["source"] == "clarification"} == {
        "Change an existing appointment only when the caller asks for it"
    }
    assert spec["data"]["open_clarifications"] == 0
    assert not any("questions wait" in s for s in spec["next_steps"])

    done = client.get(
        f"{_base(user)}/clarifications",
        headers=_headers(user),
        params={"state": "answered"},
    ).json()["data"]["data"]
    assert (done[0]["answer"], done[0]["answer_spec_version"]) == ("b", 2)
    assert done[0]["decided_by"] and done[0]["decided_at"]


def test_refusals_list_every_problem(client: TestClient, db: Session) -> None:
    user, agent, _ = _ready(db)

    bad = _raise(client, user, agent, QUESTION | {"answers": [], "category": "nope"})

    assert bad.status_code == 422
    detail = bad.json()["detail"]
    assert detail["error"] == "The questions were not stored"
    assert any("two to four answers" in s for s in detail["next_steps"])
    assert any("unknown category" in s for s in detail["next_steps"])
    assert "nothing was stored" in detail["next_steps"][-1]

    unknown = _answer(client, user, (str(uuid.uuid4()), "a"))
    assert unknown.status_code == 422
    assert "no clarification" in unknown.json()["detail"]["next_steps"][0]


def test_another_workspace_is_not_reached(client: TestClient, db: Session) -> None:
    user, agent, _ = _ready(db)
    [mine] = _raise(client, user, agent, QUESTION).json()["data"]
    stranger = _person(db)

    assert _raise(client, stranger, agent, QUESTION).status_code in (403, 404)
    elsewhere = client.post(
        f"{_base(user)}/clarifications/answers",
        headers=_headers(stranger),
        json={"answers": [{"clarification_id": mine["id"], "answer": "a"}]},
    )
    assert elsewhere.status_code in (403, 404)
    own = client.post(
        f"{_base(stranger)}/clarifications/answers",
        headers=_headers(stranger),
        json={"answers": [{"clarification_id": mine["id"], "answer": "a"}]},
    )
    assert own.status_code == 422  # not found in the stranger's own workspace
    listed = client.get(
        f"{_base(stranger)}/clarifications", headers=_headers(stranger)
    ).json()
    assert listed["data"]["data"] == []


def test_list_filters_by_agent_and_pages(client: TestClient, db: Session) -> None:
    user, agent, _ = _ready(db)
    other = _agent(db, user, "Night line")
    _catalogue(db, other, "7")
    _call(db, other, _booking(1, FULL), days_ago=1, version=7)
    write_agent_spec(
        session=db, agent=other, drafts=RULES, author=user, assistant_name=ASSISTANT
    )
    _raise(client, user, agent, QUESTION, DEPOSIT)
    _raise(client, user, other, QUESTION)

    first = client.get(
        f"{_base(user)}/clarifications",
        headers=_headers(user),
        params={"agent_id": str(agent.id), "limit": 1},
    ).json()
    assert len(first["data"]["data"]) == 1
    assert first["data"]["counts"]["open"] == 2
    assert first["next_cursor"]
    second = client.get(
        f"{_base(user)}/clarifications",
        headers=_headers(user),
        params={"agent_id": str(agent.id), "limit": 1, "cursor": first["next_cursor"]},
    ).json()
    assert second["next_cursor"] is None
    assert first["data"]["data"][0]["id"] != second["data"]["data"][0]["id"]

    readiness = client.get(f"{_base(user)}/readiness", headers=_headers(user)).json()
    assert any(
        "3 questions wait" in s and "on 2 agents" in s for s in readiness["next_steps"]
    )


def test_write_spec_and_get_agent_point_at_raising(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db)
    rules = [
        {
            "text": "Never book a slot outside opening hours",
            "category": "booking",
            "quote": "Only book within opening hours",
        }
    ]

    written = client.post(
        f"{_base(user)}/agents/{agent.id}/spec",
        headers=_headers(user),
        json={"rules": rules},
    ).json()

    assert any("raise_clarifications" in s for s in written["next_steps"])
    _raise(client, user, agent, QUESTION)
    page = client.get(f"{_base(user)}/agents/{agent.id}", headers=_headers(user)).json()
    assert any("1 question waits" in s for s in page["next_steps"])


def test_get_issue_points_at_raising_once_the_agent_has_a_spec(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db)
    _call(db, agent, _booking(1, MISSING), days_ago=1)
    issue = _issue(db, agent, "booking_details_missing")
    bare = _agent(db, user, "No spec yet")
    _call(db, bare, _booking(1, MISSING), days_ago=1)
    bare_issue = _issue(db, bare, "booking_details_missing")

    def steps(issue_id: uuid.UUID) -> list[str]:
        return client.get(
            f"{_base(user)}/issues/{issue_id}", headers=_headers(user)
        ).json()["next_steps"]

    assert any("raise_clarifications" in s for s in steps(issue.id))
    assert not any("raise_clarifications" in s for s in steps(bare_issue.id))


def test_no_answers_is_refused_with_next_steps(client: TestClient, db: Session) -> None:
    user, _, _ = _ready(db)

    empty = _answer(client, user)

    assert empty.status_code == 422
    assert empty.json()["detail"]["error"] == "Give at least one answer"
