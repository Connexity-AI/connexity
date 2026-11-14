"""Writing, reading and adopting specs through MCP and the web route, on invented calls
(plan `plans/2026-11-14-spec-api.md`)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app import crud
from app.core.config import settings
from app.models import Agent, Company, Spec, SpecRule, User
from app.models.enums import SpecOrigin
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

API = settings.API_V1_STR
PROMPT = (
    "You are the front desk of a dental clinic. Only book within opening hours, "
    "Monday to Friday. Do not discuss prices; say the clinic will send a quote."
)
RULES = [
    {
        "text": "Never book a slot outside opening hours",
        "category": "booking",
        "quote": "Only book within opening hours",
    },
    {
        "text": "Never quote a price; the clinic sends quotes",
        "category": "pricing_and_quotes",
        "quote": "do not discuss PRICES  say the clinic will send a quote",
        "touches": "money",
    },
]


def _catalogue(db: Session, agent: Agent, version: str, prompt: str = PROMPT) -> None:
    """Record ``version`` of the agent with its prompt, as version resolution would."""
    ref = agent.platform_agent_id or ""
    crud.record_component_version(
        session=db,
        agent_id=agent.id,
        company_id=agent.company_id,
        kind="prompt",
        name="LLM",
        ref="llm_invented",
        version=version,
        fingerprint=uuid.uuid4().hex,
        content={"general_prompt": prompt, "model": "invented"},
    )
    crud.record_component_version(
        session=db,
        agent_id=agent.id,
        company_id=agent.company_id,
        kind="agent",
        name=agent.name,
        ref=ref,
        version=version,
        fingerprint=uuid.uuid4().hex,
        content={"agent_name": agent.name},
        links=[{"kind": "prompt", "ref": "llm_invented", "version": version}],
    )
    db.commit()


def _setup(db: Session, version: int = 7) -> tuple[User, Agent]:
    user = _person(db)
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, str(version))
    _call(db, agent, _booking(1, FULL), days_ago=1, version=version)
    return user, agent


def _url(user: User, agent: Agent) -> str:
    return f"{API}/mcp/workspaces/{user.company_id}/agents/{agent.id}/spec"


def _write(client: TestClient, user: User, agent: Agent, rules: list[Any]) -> Any:
    return client.post(_url(user, agent), headers=_headers(user), json={"rules": rules})


def _read(client: TestClient, user: User, agent: Agent, **params: Any) -> Any:
    return client.get(_url(user, agent), headers=_headers(user), params=params)


def test_an_agent_without_a_spec_is_told_to_write_one_with_its_prompt(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)

    r = _read(client, user, agent, include_prompt="true")

    assert r.status_code == 200, r.text
    body = r.json()
    data = body["data"]
    assert (data["state"], data["spec"], data["current_agent_version"]) == (
        "none",
        None,
        "7",
    )
    assert data["prompt"]["kind"] == "prompt"
    assert data["prompt"]["content"]["general_prompt"] == PROMPT
    assert body["guide"] == "connexity://guides/spec"
    assert any("write_spec" in s for s in body["next_steps"])
    assert _read(client, user, agent).json()["data"]["prompt"] is None


def test_writing_a_spec_stores_rules_by_category_with_who_wrote_it(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)

    r = _write(client, user, agent, RULES)

    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["state"] == "current"
    assert data["spec"]["version"] == 1
    assert data["spec"]["agent_version"] == "7"
    assert data["spec"]["origin"] == "written"
    assert data["spec"]["assistant"] == "your assistant"
    assert data["spec"]["written_by"]
    assert [g["category"] for g in data["groups"]] == ["booking", "pricing_and_quotes"]
    rule = data["groups"][1]["rules"][0]
    assert (rule["source"], rule["touches"]) == ("prompt", "money")
    assert rule["key"]
    assert data["changes"] == {
        "rules": 2,
        "kept": 0,
        "added": 2,
        "dropped": 0,
        "quotes_checked": True,
    }
    spec = db.exec(select(Spec).where(Spec.agent_id == agent.id)).one()
    assert spec.created_by == user.id
    assert spec.prompt_fingerprint is not None


def test_a_second_write_is_a_new_version_counted_by_key(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)
    first = _write(client, user, agent, RULES).json()["data"]
    keys = {g["category"]: g["rules"][0]["key"] for g in first["groups"]}

    second = _write(
        client,
        user,
        agent,
        [
            RULES[0] | {"key": keys["booking"]},
            {
                "text": "Always say the clinic's name when answering",
                "category": "greeting_and_identification",
                "quote": "front desk of a dental clinic",
            },
        ],
    )

    assert second.status_code == 200, second.text
    data = second.json()["data"]
    assert data["spec"]["version"] == 2
    assert data["changes"]["kept"] == 1
    assert data["changes"]["added"] == 1
    assert data["changes"]["dropped"] == 1
    # The first version stays exactly as it was.
    old = _read(client, user, agent, version=1).json()["data"]
    assert old["spec"]["rule_count"] == 2
    assert old["latest_version"] == 2


def test_every_problem_is_refused_and_nothing_is_stored(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)

    r = _write(
        client,
        user,
        agent,
        [
            {"text": "", "category": "booking", "quote": "Only book within"},
            {"text": "A rule", "category": "nowhere", "quote": "Only book within"},
            {"text": "Invented", "category": "booking", "quote": "never on Sundays"},
            {"text": "No quote", "category": "booking"},
            {
                "text": "Old",
                "category": "booking",
                "quote": "Only book within",
                "key": "k9",
            },
        ],
    )

    assert r.status_code == 422
    steps = r.json()["detail"]["next_steps"]
    assert any("Rule 1: the text is empty" in s for s in steps)
    assert any("unknown category 'nowhere'" in s for s in steps)
    assert any("Rule 3: the quote is not in the prompt" in s for s in steps)
    assert any("Rule 4: quote the prompt's words" in s for s in steps)
    assert any("key 'k9' is not in the previous version" in s for s in steps)
    assert db.exec(select(Spec).where(Spec.agent_id == agent.id)).first() is None
    assert _write(client, user, agent, []).status_code == 422


def test_short_quotes_are_refused_and_long_lists_of_problems_say_how_many_more(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)

    short = _write(client, user, agent, [RULES[0] | {"quote": "book"}])
    assert short.status_code == 422
    assert any("at least 3 words" in s for s in short.json()["detail"]["next_steps"])

    many = _write(
        client,
        user,
        agent,
        [RULES[0] | {"category": "nowhere"} for _ in range(25)],
    )
    steps = many.json()["detail"]["next_steps"]
    assert any("and 5 more problems" in s for s in steps)


def test_an_agent_with_no_calls_cannot_have_a_spec_yet(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Quiet line")

    r = _write(client, user, agent, RULES)

    assert r.status_code == 422
    assert "no calls yet" in r.json()["detail"]["error"]


def test_quotes_are_stored_unchecked_when_connexity_has_no_prompt(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agent = _agent(db, user, "No catalogue")
    _call(db, agent, _booking(1, FULL), days_ago=1, version=3)

    r = _write(client, user, agent, [RULES[0] | {"quote": "anything at all"}])

    assert r.status_code == 200, r.text
    assert r.json()["data"]["changes"]["quotes_checked"] is False
    assert any("not checked" in s for s in r.json()["next_steps"])


def test_a_call_on_a_new_agent_version_adopts_the_spec_once(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)
    written = _write(client, user, agent, RULES).json()["data"]
    _catalogue(db, agent, "8")

    _call(db, agent, _booking(1, FULL), days_ago=0, version=8)
    _call(db, agent, _booking(1, FULL), days_ago=0, version=8)
    # A late, older call on the old version changes nothing.
    _call(db, agent, _booking(1, FULL), days_ago=3, version=7)

    specs = db.exec(
        select(Spec).where(Spec.agent_id == agent.id).order_by(col(Spec.version))
    ).all()
    assert [(s.version, s.agent_version, s.origin) for s in specs] == [
        (1, "7", SpecOrigin.WRITTEN),
        (2, "8", SpecOrigin.ADOPTED),
    ]
    assert specs[1].created_by is None
    adopted = db.exec(select(SpecRule).where(SpecRule.spec_id == specs[1].id)).all()
    keys = {g["rules"][0]["key"] for g in written["groups"]}
    assert {r.key for r in adopted} == keys

    body = _read(client, user, agent).json()
    assert body["data"]["state"] == "needs_review"
    assert any("moved to version 8" in s for s in body["next_steps"])
    # The review: a normal new version on top of the adopted one.
    again = _write(
        client,
        user,
        agent,
        [RULES[0] | {"key": written["groups"][0]["rules"][0]["key"]}],
    ).json()["data"]
    assert (again["spec"]["version"], again["state"]) == (3, "current")


def test_an_agent_without_a_spec_adopts_nothing(
    client: TestClient, db: Session
) -> None:
    _, agent = _setup(db)
    _call(db, agent, _booking(1, FULL), days_ago=0, version=8)

    assert db.exec(select(Spec).where(Spec.agent_id == agent.id)).first() is None


def test_list_agents_and_readiness_say_which_specs_are_missing(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)
    headers = _headers(user)
    base = f"{API}/mcp/workspaces/{user.company_id}"

    listed = client.get(f"{base}/agents", headers=headers).json()
    assert [(a["spec"], a["spec_version"]) for a in listed["data"]] == [("none", None)]
    assert any("write_spec" in s for s in listed["next_steps"])

    # Before the first scan, Readiness does not ask for the spec yet.
    readiness = client.get(f"{base}/readiness", headers=headers).json()
    assert not any("spec" in s for s in readiness["next_steps"])
    company = db.get(Company, user.company_id)
    assert company is not None
    company.first_scan_done_at = datetime.now(UTC)
    db.add(company)
    db.commit()
    readiness = client.get(f"{base}/readiness", headers=headers).json()
    assert any(
        "Write each agent's spec" in s and "Front desk" in s
        for s in readiness["next_steps"]
    )

    _write(client, user, agent, RULES)
    listed = client.get(f"{base}/agents", headers=headers).json()
    assert [(a["spec"], a["spec_version"]) for a in listed["data"]] == [("current", 1)]
    assert not any("write_spec" in s for s in listed["next_steps"])
    readiness = client.get(f"{base}/readiness", headers=headers).json()
    assert not any("Write each agent's spec" in s for s in readiness["next_steps"])


def test_the_web_route_reads_the_open_workspaces_spec(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, "7")
    _call(db, agent, _booking(1, FULL), days_ago=1, version=7)
    assert _write(client, user, agent, RULES).status_code == 200

    r = client.get(f"{API}/agents/{agent.id}/spec", cookies=cookies)
    assert r.status_code == 200, r.text
    assert r.json()["spec"]["rule_count"] == 2
    assert r.json()["prompt"] is None
    assert (
        client.get(
            f"{API}/agents/{agent.id}/spec", cookies=cookies, params={"version": 9}
        ).status_code
        == 404
    )

    other = _person(db)
    elsewhere = _agent(db, other, "Elsewhere")
    assert (
        client.get(f"{API}/agents/{elsewhere.id}/spec", cookies=cookies).status_code
        == 404
    )


def test_another_workspace_and_unknown_agents_are_not_found(
    client: TestClient, db: Session
) -> None:
    user, agent = _setup(db)
    other = _person(db)

    stranger = client.get(_url(user, agent), headers=_headers(other))
    assert stranger.status_code == 404
    missing = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/agents/{uuid.uuid4()}/spec",
        headers=_headers(user),
    )
    assert missing.status_code == 404
    assert _read(client, user, agent, version=4).status_code == 404
