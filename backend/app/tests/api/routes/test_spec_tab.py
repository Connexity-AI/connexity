"""The spec as the Spec tab reads it: versions, sources, conflicts and comparing, on
invented agents and calls (plan `plans/2026-11-15-spec-tab.md`)."""

from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import Agent, User
from app.services.clarification import (
    Decision,
    answer_clarifications,
    raise_clarifications,
)
from app.services.spec import write_agent_spec
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_issues_list import _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _headers,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_spec_api import _catalogue
from app.tests.services.test_clarifications import (
    ASSISTANT,
    CHANGE,
    DEPOSIT,
    RULES,
    _ready,
)

API = settings.API_V1_STR


def _answered(db: Session, user: User, agent: Agent) -> None:
    """Version 2: the first spec plus the answer to CHANGE (b)."""
    [change] = raise_clarifications(
        session=db,
        agent=agent,
        drafts=[CHANGE],
        raised_by=user,
        assistant_name=ASSISTANT,
    )
    answer_clarifications(
        session=db,
        company_id=user.company_id,
        decisions=[Decision(change.id, "b")],
        decided_by=user,
        assistant_name=ASSISTANT,
    )


def _rules(body: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for g in body["groups"] for r in g["rules"]]


def test_the_spec_has_versions_sources_and_conflicts(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db)
    _answered(db, user, agent)
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    answered_key = next(
        r.key
        for r in crud.spec_rules(session=db, spec_id=spec.id)
        if r.clarification_id is not None
    )
    raise_clarifications(
        session=db,
        agent=agent,
        drafts=[
            CHANGE._replace(
                question="The new prompt lets callers move appointments. Change it?",
                replaces_key=answered_key,
            ),
            DEPOSIT,
        ],
        raised_by=user,
        assistant_name=ASSISTANT,
    )
    body = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents/{agent.id}/spec",
        headers=_headers(user),
    ).json()["data"]

    assert [v["version"] for v in body["versions"]] == [2, 1]
    assert [v["origin"] for v in body["versions"]] == ["answered", "written"]
    assert body["counts"] == {
        "from_prompt": len(RULES),
        "from_clarifications": 1,
        "in_conflict": 1,
    }
    assert body["open_clarifications"] == 2
    answered = next(r for r in _rules(body) if r["source"] == "clarification")
    assert answered["answered_by"] and answered["answered_at"]
    assert answered["in_conflict"] is True
    assert all(r["change"] is None for r in _rules(body))
    assert not any(r["in_conflict"] for r in _rules(body) if r["key"] != answered_key)

    # An earlier version shows no conflicts: they are about the rules now.
    first = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents/{agent.id}/spec",
        headers=_headers(user),
        params={"version": 1},
    ).json()["data"]
    assert first["counts"]["in_conflict"] == 0


def test_comparing_marks_kept_added_and_dropped(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db)
    _answered(db, user, agent)
    # Version 3 rewrites the prompt rules: the first is kept, the second dropped.
    v2 = crud.latest_spec(session=db, agent_id=agent.id)
    assert v2 is not None
    keep = next(
        r.key
        for r in crud.spec_rules(session=db, spec_id=v2.id)
        if r.text == RULES[0].text
    )
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[RULES[0]._replace(key=keep)],
        author=user,
        assistant_name=ASSISTANT,
    )
    body = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents/{agent.id}/spec",
        headers=_headers(user),
        params={"compare": 1},
    ).json()["data"]

    assert body["comparison"] == {"version": 1, "kept": 1, "added": 1, "dropped": 1}
    changes = {r["text"]: r["change"] for r in _rules(body)}
    assert changes[RULES[0].text] == "kept"
    assert changes[RULES[1].text] == "dropped"
    assert (
        changes["Change an existing appointment only when the caller asks for it"]
        == "added"
    )
    # The dropped rule sits in its own category.
    pricing = next(g for g in body["groups"] if g["category"] == "pricing_and_quotes")
    assert [r["change"] for r in pricing["rules"]] == ["dropped"]


def test_a_changed_text_reads_as_dropped_and_added(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db)
    _answered(db, user, agent)
    v2 = crud.latest_spec(session=db, agent_id=agent.id)
    assert v2 is not None
    key = next(
        r.key
        for r in crud.spec_rules(session=db, spec_id=v2.id)
        if r.clarification_id is not None
    )
    [replacing] = raise_clarifications(
        session=db,
        agent=agent,
        drafts=[CHANGE._replace(question="Move appointments now?", replaces_key=key)],
        raised_by=user,
        assistant_name=ASSISTANT,
    )
    answer_clarifications(
        session=db,
        company_id=user.company_id,
        decisions=[Decision(replacing.id, "c")],
        decided_by=user,
        assistant_name=ASSISTANT,
    )

    body = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents/{agent.id}/spec",
        headers=_headers(user),
        params={"compare": 2},
    ).json()["data"]

    same_key = [r for r in _rules(body) if r["key"] == key]
    assert sorted((r["text"], r["change"]) for r in same_key) == [
        ("Change an existing appointment only when the caller asks for it", "dropped"),
        ("Never change an existing appointment", "added"),
    ]
    assert body["comparison"] == {
        "version": 2,
        "kept": len(RULES),
        "added": 1,
        "dropped": 1,
    }


def test_the_web_route_compares_and_refuses_unknown_versions(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, "7")
    _call(db, agent, _booking(1, FULL), days_ago=1, version=7)
    write_agent_spec(
        session=db, agent=agent, drafts=RULES, author=user, assistant_name=ASSISTANT
    )
    _answered(db, user, agent)
    url = f"{API}/agents/{agent.id}/spec"

    compared = client.get(url, cookies=cookies, params={"compare": 1})
    assert compared.status_code == 200, compared.text
    assert compared.json()["comparison"]["added"] == 1
    assert client.get(url, cookies=cookies, params={"compare": 9}).status_code == 404
    other = _agent(db, _person(db), "Elsewhere")
    assert (
        client.get(f"{API}/agents/{other.id}/spec", cookies=cookies).status_code == 404
    )
    mcp = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents/{agent.id}/spec",
        headers=_headers(user),
        params={"compare": 9},
    )
    assert mcp.status_code == 404
    assert "no spec version 9" in mcp.json()["detail"]["error"]
