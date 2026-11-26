"""Each spec rule's check type and the call inputs it needs, and what a check is given,
on invented agents and calls (plan `plans/2026-11-26-rule-data-and-check.md`)."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.models import Agent, Call, SpecRule
from app.models.enums import SpecCheckType
from app.services.rule_context import NOT_SET, rules_with_clarifications
from app.services.rule_judge import RuleToJudge, _user_prompt
from app.services.spec import (
    SpecRefused,
    refused_input,
    spec_answer,
    write_agent_spec,
)
from app.tests.api.routes.test_mcp_issues import _settings  # noqa: F401
from app.tests.api.routes.test_spec_api import RULES as API_RULES
from app.tests.api.routes.test_spec_api import _read, _setup, _write
from app.tests.services.test_clarifications import ASSISTANT, RULES, _ready

HISTORY = "Earlier call: the prospect asked to be called back next week. " * 4
INPUTS = {
    "attempt_number": "2",
    "previous_conversations": HISTORY,  # long: over 200 characters
    "customer_email": "sam@example.com",
    "lead_id": "invented-lead",
}


def _give_inputs(db: Session, agent: Agent) -> None:
    """The agent's calls carry the invented inputs."""
    for call in db.exec(select(Call).where(Call.agent_id == agent.id)).all():
        call.inputs = INPUTS
        db.add(call)
    db.commit()


def _rules(db: Session, agent: Agent) -> dict[str, SpecRule]:
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    return {r.text: r for r in crud.spec_rules(session=db, spec_id=spec.id)}


def test_a_new_rule_is_a_classifier_on_the_call_alone_and_marks_carry_by_key(
    db: Session,
) -> None:
    user, agent, _ = _ready(db)
    _give_inputs(db, agent)
    first = _rules(db, agent)
    hours, price = first[RULES[0].text], first[RULES[1].text]
    assert (hours.check, hours.inputs) == (SpecCheckType.CLASSIFIER, [])

    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(
                key=hours.key,
                check=SpecCheckType.CLASSIFIER_THEN_LLM,
                inputs=["attempt_number", "attempt_number"],
            ),
            RULES[1]._replace(key=price.key),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )
    second = _rules(db, agent)
    assert (second[RULES[0].text].check, second[RULES[0].text].inputs) == (
        SpecCheckType.CLASSIFIER_THEN_LLM,
        ["attempt_number"],  # given twice, stored once
    )
    assert second[RULES[1].text].check is SpecCheckType.CLASSIFIER

    # Kept without them: they carry by key, as the critical mark does.
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[RULES[0]._replace(key=hours.key), RULES[1]._replace(key=price.key)],
        author=user,
        assistant_name=ASSISTANT,
    )
    third = _rules(db, agent)
    assert (third[RULES[0].text].check, third[RULES[0].text].inputs) == (
        SpecCheckType.CLASSIFIER_THEN_LLM,
        ["attempt_number"],
    )


def test_inputs_must_be_known_short_enough_and_never_personal(db: Session) -> None:
    user, agent, _ = _ready(db)
    _give_inputs(db, agent)

    with pytest.raises(SpecRefused) as refused:
        write_agent_spec(
            session=db,
            agent=agent,
            drafts=[
                RULES[0]._replace(inputs=["no_such_input"]),
                RULES[1]._replace(inputs=["customer_email", "lead_id"]),
                RULES[0]._replace(
                    text="Call history", inputs=["previous_conversations"]
                ),
                RULES[0]._replace(text="Too many", inputs=[f"x{n}" for n in range(11)]),
            ],
            author=user,
            assistant_name=ASSISTANT,
        )

    joined = " | ".join(refused.value.problems)
    for expected in (
        "Rule 1: no call of this agent in the last 30 days carries an input named "
        "'no_such_input'. Known inputs: attempt_number, customer_email, lead_id, "
        "previous_conversations.",
        "Rule 2: input 'customer_email' is refused: it is a contact detail or an id",
        "Rule 2: input 'lead_id' is refused",
        "Rule 3: it needs long text (previous_conversations), which goes only to the "
        "LLM step; choose `classifier_then_llm` or `llm`.",
        "Rule 4: at most 10 inputs, not 11.",
    ):
        assert expected in joined

    # The same long input with an LLM step is fine.
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(
                text="Call history", inputs=["previous_conversations"], check="llm"
            )
        ],
        author=user,
        assistant_name=ASSISTANT,
    )


@pytest.mark.parametrize(
    ("name", "refused"),
    [
        ("attempt_number", False),
        ("customer_name", False),
        ("listing_address_short", False),
        ("customer_email", True),
        ("customer_phone", True),
        ("caller_number", True),
        ("p-asserted-identity", True),
        ("twilio-callsid", True),
        ("voice_agent_id", True),
        ("id", True),
        ("api_token", True),
    ],
)
def test_contact_details_ids_and_secrets_are_never_inputs(
    name: str, refused: bool
) -> None:
    assert (refused_input(name) is not None) is refused


def test_get_spec_answers_each_rules_data_and_the_known_inputs(db: Session) -> None:
    user, agent, _ = _ready(db)
    _give_inputs(db, agent)
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(inputs=["attempt_number"]),
            RULES[1]._replace(inputs=["previous_conversations"], check="llm"),
            RULES[0]._replace(text="Greet the caller by the clinic's name"),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )

    answer = spec_answer(session=db, agent=agent)

    assert answer is not None and answer.counts is not None
    by_text = {r.text: r for g in answer.groups for r in g.rules}
    assert (by_text[RULES[0].text].data, by_text[RULES[1].text].data) == (
        "short_inputs",
        "long_text",
    )
    assert by_text["Greet the caller by the clinic's name"].data == "call"
    assert answer.counts.classifier_on_call == 1
    known = {k.name: k for k in answer.known_inputs}
    assert set(known) == set(INPUTS)
    assert (known["previous_conversations"].long, known["attempt_number"].long) == (
        True,
        False,
    )
    assert (known["customer_email"].allowed, known["attempt_number"].allowed) == (
        False,
        True,
    )
    assert known["attempt_number"].calls == 2
    # Never a value.
    dumped = answer.model_dump_json()
    assert "sam@example.com" not in dumped and "invented-lead" not in dumped


def test_a_check_is_given_only_its_inputs_and_short_ones_to_the_classifier(
    db: Session,
) -> None:
    user, agent, _ = _ready(db)
    _give_inputs(db, agent)
    with pytest.raises(SpecRefused):  # "form_answer" is not one the calls carry
        write_agent_spec(
            session=db,
            agent=agent,
            drafts=[
                RULES[0]._replace(
                    inputs=["attempt_number", "previous_conversations", "form_answer"],
                    check="classifier_then_llm",
                ),
                RULES[1],
            ],
            author=user,
            assistant_name=ASSISTANT,
        )
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None and spec.version == 1
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(
                inputs=["attempt_number", "previous_conversations"],
                check="classifier_then_llm",
            ),
            RULES[1],
        ],
        author=user,
        assistant_name=ASSISTANT,
    )
    rules = list(_rules(db, agent).values())
    read = rules_with_clarifications(session=db, agent_id=agent.id, rules=rules)
    hours = next(r for r in read.values() if r.text == RULES[0].text)
    price = next(r for r in read.values() if r.text == RULES[1].text)
    values = INPUTS | {"unrelated": "x"}

    assert hours.given(values, llm=False) == {"attempt_number": "2"}
    assert hours.given(values, llm=True) == {
        "attempt_number": "2",
        "previous_conversations": HISTORY,
    }
    assert hours.given({}, llm=False) == {"attempt_number": NOT_SET}
    assert price.given(values, llm=True) == {}
    # The check type and input names are part of the fingerprint.
    assert (
        hours.fingerprint != hours.__class__(key=hours.key, text=hours.text).fingerprint
    )


@pytest.mark.usefixtures("db")
def test_the_judge_reads_a_rules_inputs() -> None:
    prompt = _user_prompt(
        [],
        [
            RuleToJudge(
                key="k1",
                text="On a first call, never say the form was just filled out",
                inputs=(("attempt_number", "2"), ("form_answer", NOT_SET)),
            )
        ],
        None,
        [],
    )

    assert (
        "- [k1] On a first call, never say the form was just filled out\n"
        "  Input attempt_number: 2\n"
        "  Input form_answer: not set"
    ) in prompt


def test_check_and_inputs_through_mcp(client: TestClient, db: Session) -> None:
    user, agent = _setup(db)
    _give_inputs(db, agent)

    refused = _write(
        client, user, agent, [API_RULES[0] | {"inputs": ["customer_email"]}]
    )
    assert refused.status_code == 422
    assert any(
        "contact detail or an id" in s for s in refused.json()["detail"]["next_steps"]
    )

    written = _write(
        client,
        user,
        agent,
        [
            API_RULES[0]
            | {"check": "classifier_then_llm", "inputs": ["attempt_number"]},
            API_RULES[1],
        ],
    )

    assert written.status_code == 200, written.text
    body = written.json()
    rules = {r["text"]: r for g in body["data"]["groups"] for r in g["rules"]}
    first = rules[API_RULES[0]["text"]]
    assert (first["check"], first["inputs"], first["data"]) == (
        "classifier_then_llm",
        ["attempt_number"],
        "short_inputs",
    )
    assert body["data"]["counts"]["classifier_on_call"] == 1
    assert any("classifier checks on the call alone" in s for s in body["next_steps"])
    read = _read(client, user, agent).json()
    names = {k["name"] for k in read["data"]["known_inputs"]}
    assert "attempt_number" in names
    assert any("only to the LLM" in r for r in read["rules"])
