"""The Action items web routes: listing, answering, parking and reopening as the
person, on invented agents and calls (plan `plans/2026-11-15-action-items.md`)."""

import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.tests.api.routes.test_issues_list import _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    _agent,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.services.test_clarifications import CHANGE, DEPOSIT, _raise, _ready

API = settings.API_V1_STR


def _decide(
    client: TestClient, cookies: dict[str, str], *answers: tuple[str, str]
) -> Any:
    return client.post(
        f"{API}/clarifications/answers",
        cookies=cookies,
        json={"answers": [{"clarification_id": i, "answer": a} for i, a in answers]},
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
        "suggested_confident": 0,
    }

    answered = _decide(
        client, cookies, (str(change.id), "b"), (str(deposit.id), "park")
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["specs"][0]["rules_added"] == 1
    week = client.get(
        f"{API}/clarifications",
        cookies=cookies,
        params={"state": "answered", "this_week": True},
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


def test_a_batch_of_confident_suggestions_across_two_agents(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    _, front, _ = _ready(db, owner=user)
    _, night, _ = _ready(db, owner=user)
    sure = {"suggested_answer": "c", "suggestion_why": "The prompt says so."}
    a, b = _raise(
        db,
        user,
        front,
        CHANGE._replace(**sure, suggestion_confident=True),
        DEPOSIT._replace(suggested_answer="b", suggestion_why="Unsure."),
    )
    [c] = _raise(db, user, night, CHANGE._replace(**sure, suggestion_confident=True))

    batch = client.get(
        f"{API}/clarifications",
        cookies=cookies,
        params={"confident": True, "limit": 200},
    ).json()
    assert {x["id"] for x in batch["data"]} == {str(a.id), str(c.id)}
    assert batch["counts"]["suggested_confident"] == 2

    done = _decide(client, cookies, (str(a.id), "c"), (str(c.id), "c"))

    assert done.status_code == 200, done.text
    specs = done.json()["specs"]
    assert sorted(s["rules_added"] for s in specs) == [1, 1]
    assert {s["agent_id"] for s in specs} == {str(front.id), str(night.id)}
    left = client.get(
        f"{API}/clarifications", cookies=cookies, params={"confident": True}
    ).json()
    assert left["data"] == []
    assert str(b.id) in {
        x["id"]
        for x in client.get(f"{API}/clarifications", cookies=cookies).json()["data"]
    }
