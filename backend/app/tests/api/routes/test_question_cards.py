"""The clarification web routes behind the question cards on Work: listing,
answering (a to d, or "other" with the person's words), parking and reopening as the
person, on invented agents and calls (plans `plans/2026-11-15-action-items.md` and
`plans/2026-11-16-question-cards.md`)."""

import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.tests.api.routes.test_issues_list import _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    _agent,
    _headers,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.services.test_clarifications import CHANGE, DEPOSIT, _raise, _ready

API = settings.API_V1_STR


def _decide(
    client: TestClient, cookies: dict[str, str], *answers: tuple[str, ...]
) -> Any:
    return client.post(
        f"{API}/clarifications/answers",
        cookies=cookies,
        json={
            "answers": [
                {
                    "clarification_id": a[0],
                    "answer": a[1],
                    "text": a[2] if len(a) > 2 else None,
                }
                for a in answers
            ]
        },
    )


def test_the_person_lists_answers_parks_and_reopens(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    _, agent, calls = _ready(db, owner=user)
    change, deposit = _raise(db, user, agent, CHANGE._replace(call_ids=calls), DEPOSIT)

    listed = client.get(f"{API}/clarifications", cookies=cookies)

    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert [c["id"] for c in body["data"]] == [str(change.id), str(deposit.id)]
    assert body["counts"] == {
        "open": 2,
        "answered": 0,
        "parked": 0,
        "answered_this_week": 0,
    }

    answered = _decide(
        client, cookies, (str(change.id), "b"), (str(deposit.id), "park")
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["specs"][0]["rules_added"] == 1
    week = client.get(
        f"{API}/clarifications",
        cookies=cookies,
        params={"state": "answered"},
    ).json()
    assert week["counts"]["answered_this_week"] == 1
    assert week["data"][0]["decided_assistant"] is None  # answered in the app
    assert week["data"][0]["decided_by"]
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None and spec.assistant_name is None

    reopened = _decide(client, cookies, (str(deposit.id), "reopen"))
    assert reopened.json()["reopened"] == 1
    assert (
        client.get(f"{API}/clarifications", cookies=cookies).json()["counts"]["open"]
        == 1
    )


def test_refusals_and_other_workspaces(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    _, agent, _ = _ready(db, owner=user)
    [change] = _raise(db, user, agent, CHANGE)
    _decide(client, cookies, (str(change.id), "a"))

    again = _decide(client, cookies, (str(change.id), "b"))
    assert again.status_code == 422
    assert "already answered" in again.json()["detail"]["problems"][0]

    _, stranger_cookies = _signed_in(client, db)
    theirs = _decide(client, stranger_cookies, (str(change.id), "park"))
    assert theirs.status_code == 422
    assert "no clarification" in theirs.json()["detail"]["problems"][0]
    assert (
        client.get(f"{API}/clarifications", cookies=stranger_cookies).json()["data"]
        == []
    )
    other = _agent(db, _person(db), "Elsewhere")
    assert (
        client.get(
            f"{API}/clarifications", cookies=cookies, params={"agent_id": str(other.id)}
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"{API}/clarifications",
            cookies=cookies,
            params={"agent_id": str(uuid.uuid4())},
        ).status_code
        == 404
    )


def test_something_else_becomes_the_rule_as_written(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    _, agent, _ = _ready(db, owner=user)
    change, deposit = _raise(db, user, agent, CHANGE, DEPOSIT)
    before = crud.latest_spec(session=db, agent_id=agent.id)
    assert before is not None
    words = "Change an appointment only when the caller gives their date of birth"

    empty = _decide(client, cookies, (str(change.id), "other", "  "))
    answered = _decide(
        client, cookies, (str(change.id), "other", words), (str(deposit.id), "b")
    )

    assert empty.status_code == 422
    assert "needs the person's answer as text" in str(empty.json())
    assert answered.status_code == 200, answered.text
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None and spec.version == before.version + 1  # one version
    rules = {r.text for r in crud.spec_rules(session=db, spec_id=spec.id)}
    assert words in rules and "Never mention a deposit" in rules
    shown = client.get(
        f"{API}/clarifications",
        cookies=cookies,
        params={"state": "answered", "agent_id": str(agent.id)},
    ).json()["data"]
    other = next(c for c in shown if c["id"] == str(change.id))
    assert (other["answer"], other["answer_text"]) == ("other", words)


def test_something_else_through_mcp(client: TestClient, db: Session) -> None:
    user = _person(db)
    _, agent, _ = _ready(db, owner=user)
    [change] = _raise(db, user, agent, CHANGE)

    r = client.post(
        f"{API}/mcp/workspaces/{user.company_id}/clarifications/answers",
        headers=_headers(user),
        json={
            "answers": [
                {
                    "clarification_id": str(change.id),
                    "answer": "other",
                    "text": "Ask first",
                }
            ]
        },
    )

    assert r.status_code == 200, r.text
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    assert "Ask first" in {r.text for r in crud.spec_rules(session=db, spec_id=spec.id)}
