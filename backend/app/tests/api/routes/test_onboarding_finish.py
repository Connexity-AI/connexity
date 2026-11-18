"""Onboarding ends with a complete dashboard (roadmap 10.192; plan
`plans/2026-11-18-onboarding-ends-with-dashboard.md`): the questions are its last step,
the person confirms proposed answers in a batch, and the moment it completes is stored
once. Agents and calls are invented."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.crud import readiness as crud_readiness
from app.models import Agent, Company, User
from app.models.check import DecisionRecord
from app.models.clarification import Clarification
from app.models.readiness import ReadinessStepState
from app.tests.api.routes.test_mcp_clarifications import (
    DEPOSIT,
    QUESTION,
    _base,
    _raise,
)
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    _headers,
    _settings,  # the autouse fixture that sets up MCP sign-in
)
from app.tests.services.test_clarifications import _ready


def _set_up(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> tuple[User, Agent]:
    """A workspace through scan and specs: every Readiness step done, one agent with
    its spec written, no question raised yet."""
    user, agent, _ = _ready(db)
    now = datetime.now(UTC)
    agent.scan_done_at = now
    db.add(agent)
    company = db.get(Company, user.company_id)
    assert company is not None
    company.first_scan_done_at = now
    db.add(company)
    db.commit()
    # An assistant is connected (in the product, through OAuth or a personal token).
    monkeypatch.setattr(
        crud_readiness, "connected_assistants", lambda **_: ["Claude Code"]
    )
    readiness = crud.get_readiness(session=db, company_id=user.company_id, mcp_url=None)
    assert {s.state for s in readiness.steps} == {ReadinessStepState.DONE}
    return user, agent


def _next(client: TestClient, user: User) -> dict[str, Any]:
    response = client.get(
        f"{_base(user)}/next-task",
        headers=_headers(user),
        params={"session": "Onboarding"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _completed_at(db: Session, user: User) -> datetime | None:
    db.expire_all()
    company = db.get(Company, user.company_id)
    assert company is not None
    return company.onboarding_completed_at


def _dashboard(client: TestClient, user: User) -> dict[str, Any]:
    response = client.get(f"{_base(user)}/dashboard", headers=_headers(user))
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_questions_then_a_confirmed_batch_complete_onboarding(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, agent = _set_up(client, db, monkeypatch)

    # The specs are written, but the questions step comes first: not complete yet.
    first = _next(client, user)
    task = first["data"]["task"]
    assert task["key"] == "onboarding:answers"
    assert task["title"] == "Answer the open questions"
    assert any("`proposed`" in step for step in first["next_steps"])
    assert not any("dashboard is ready" in step for step in first["next_steps"])
    assert _completed_at(db, user) is None
    strip = _dashboard(client, user)["onboarding"]
    assert [s["done"] for s in strip["steps"]] == [True, True, True, False]

    raised = _raise(client, user, agent, QUESTION, DEPOSIT)
    assert raised.status_code == 200, raised.text
    change, deposit = (item["id"] for item in raised.json()["data"])
    assert _dashboard(client, user)["onboarding"]["steps"][2] == {
        "key": "answers",
        "label": "Answers 0 of 2",
        "done": False,
    }
    # While onboarding runs, the questions are setup; the questions row gives way.
    listed = client.get(f"{_base(user)}/tasks", headers=_headers(user)).json()
    keys = [t["key"] for t in listed["data"]["tasks"]]
    assert f"clarifications:{agent.id}" in keys and "onboarding:answers" not in keys

    # The person confirms the proposed answer and parks the other, in one batch.
    answered = client.post(
        f"{_base(user)}/clarifications/answers",
        headers=_headers(user),
        json={
            "answers": [
                {"clarification_id": change, "answer": "b", "proposed": True},
                {"clarification_id": deposit, "answer": "park"},
            ]
        },
    )

    assert answered.status_code == 200, answered.text
    body = answered.json()
    ready = body["next_steps"][0]
    assert 'Your dashboard is ready"' in ready and "/dashboard" in ready
    assert _completed_at(db, user) is not None
    stored = db.get(Clarification, change)
    assert stored is not None and stored.answer_proposed is True
    record = db.exec(
        select(DecisionRecord).where(DecisionRecord.subject == change)
    ).one()
    assert record.detail is not None and record.detail["proposed"] is True
    shown = client.get(
        f"{_base(user)}/clarifications",
        headers=_headers(user),
        params={"state": "answered"},
    ).json()["data"]["data"]
    assert [(c["answer"], c["answer_proposed"]) for c in shown] == [("b", True)]
    after = _dashboard(client, user)
    assert after["onboarding"] is None
    assert "onboarding" not in (after["score"]["why_none"] or "")

    # A question raised later does not reopen onboarding.
    again = _raise(
        client,
        user,
        agent,
        QUESTION | {"question": "May the agent book two slots for one caller?"},
    )
    assert again.status_code == 200, again.text
    assert _completed_at(db, user) is not None
    assert _dashboard(client, user)["onboarding"] is None
    # ...and its questions go back to the other work.
    answering = client.post(
        f"{_base(user)}/clarifications/answers",
        headers=_headers(user),
        json={
            "answers": [
                {"clarification_id": again.json()["data"][0]["id"], "answer": "a"}
            ]
        },
    )
    assert not any("dashboard is ready" in s for s in answering.json()["next_steps"])


def test_nothing_to_ask_completes_on_the_next_task(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, _ = _set_up(client, db, monkeypatch)

    assert _next(client, user)["data"]["task"]["key"] == "onboarding:answers"
    # The assistant found nothing the specs leave open, and asks for its next task.
    after = _next(client, user)

    assert 'Your dashboard is ready"' in after["next_steps"][0]
    assert _completed_at(db, user) is not None
    assert after["data"]["previous"]["state"] == "done"
    # Only once.
    assert not any("dashboard is ready" in s for s in _next(client, user)["next_steps"])


def test_proposed_is_only_for_an_answer(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, agent = _set_up(client, db, monkeypatch)
    [question] = _raise(client, user, agent, QUESTION).json()["data"]

    refused = client.post(
        f"{_base(user)}/clarifications/answers",
        headers=_headers(user),
        json={
            "answers": [
                {"clarification_id": question["id"], "answer": "park", "proposed": True}
            ]
        },
    )

    assert refused.status_code == 422
    assert "'proposed'" in refused.json()["detail"]["next_steps"][0]
    assert _completed_at(db, user) is None
