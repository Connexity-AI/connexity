"""Raising, answering and parking clarifications, and how answers become spec rules,
on invented agents and calls (plan `plans/2026-11-15-clarifications.md`)."""

import uuid
from collections.abc import Callable

import pytest
from sqlmodel import Session, col, select

from app import crud
from app.crud.clarification import (
    list_page,
    open_counts,
    state_counts,
)
from app.crud.spec import adopt_spec_safely
from app.models import Agent, Spec, SpecRule, User
from app.models.check import DecisionRecord
from app.models.clarification import Clarification
from app.models.enums import (
    ClarificationState,
    DecisionKind,
    SpecOrigin,
    SpecRuleSource,
    SpecRuleTouches,
)
from app.services.clarification import (
    AnswerDraft,
    AnswerResult,
    ClarificationRefused,
    Decision,
    QuestionDraft,
    answer_clarifications,
    raise_clarifications,
)
from app.services.spec import RuleDraft, SpecRefused, spec_state, write_agent_spec
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_spec_api import _catalogue

ASSISTANT = "Claude Code"
RULES = [
    RuleDraft(
        text="Never book a slot outside opening hours",
        category="booking",
        quote="Only book within opening hours",
        touches=None,
        key=None,
    ),
    RuleDraft(
        text="Never quote a price; the clinic sends quotes",
        category="pricing_and_quotes",
        quote="say the clinic will send a quote",
        touches=SpecRuleTouches.MONEY,
        key=None,
    ),
]
CHANGE = QuestionDraft(
    question="The agent changed an existing appointment on 2 calls. Is it allowed to?",
    answers=[
        AnswerDraft("Yes, always", "The agent may change an existing appointment"),
        AnswerDraft(
            "Only when the caller asks",
            "Change an existing appointment only when the caller asks for it",
        ),
        AnswerDraft("Never", "Never change an existing appointment"),
    ],
    category="booking",
)
DEPOSIT = QuestionDraft(
    question="Callers asked about a deposit. May the agent say one is needed?",
    answers=[
        AnswerDraft("Yes", "Tell callers a deposit is needed for new patients"),
        AnswerDraft("No", "Never mention a deposit"),
    ],
    category="pricing_and_quotes",
    touches=SpecRuleTouches.MONEY,
)


def _ready(
    db: Session, version: int = 7, owner: User | None = None
) -> tuple[User, Agent, list[uuid.UUID]]:
    """A person (``owner`` if given) and an agent with two calls on ``version`` and a
    written spec."""
    user = owner or _person(db)
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, str(version))
    calls = [
        _call(db, agent, _booking(1, FULL), days_ago=d, version=version) for d in (2, 1)
    ]
    write_agent_spec(
        session=db, agent=agent, drafts=RULES, author=user, assistant_name=ASSISTANT
    )
    return user, agent, calls


def _raise(
    db: Session, user: User, agent: Agent, *drafts: QuestionDraft
) -> list[Clarification]:
    return raise_clarifications(
        session=db,
        agent=agent,
        drafts=list(drafts),
        raised_by=user,
        assistant_name=ASSISTANT,
    )


def _answer(db: Session, user: User, *decisions: tuple[uuid.UUID, str]) -> object:
    return answer_clarifications(
        session=db,
        company_id=user.company_id,
        decisions=[Decision(i, a) for i, a in decisions],
        decided_by=user,
        assistant_name=ASSISTANT,
    )


def _refused(do: Callable[[], object]) -> list[str]:
    with pytest.raises(ClarificationRefused) as refused:
        do()
    return refused.value.problems


def _rules(db: Session, spec: Spec) -> list[SpecRule]:
    return crud.spec_rules(session=db, spec_id=spec.id)


def _count(db: Session, agent: Agent) -> int:
    return len(
        db.exec(select(Clarification).where(Clarification.agent_id == agent.id)).all()
    )


def test_raising_stores_open_questions_with_their_calls(db: Session) -> None:
    user, agent, calls = _ready(db)
    spec = crud.latest_spec(session=db, agent_id=agent.id)

    stored = _raise(
        db, user, agent, CHANGE._replace(call_ids=[*calls, calls[0]]), DEPOSIT
    )

    change, deposit = stored
    assert change.state is ClarificationState.OPEN
    assert spec is not None and change.spec_id == spec.id
    assert change.call_ids == [str(c) for c in calls]  # duplicates dropped
    assert [a["label"] for a in change.answers] == [
        "Yes, always",
        "Only when the caller asks",
        "Never",
    ]
    assert (change.raised_by, change.raised_assistant) == (user.id, ASSISTANT)
    assert deposit.call_ids == []  # a question from a prompt change has no calls
    assert deposit.touches is SpecRuleTouches.MONEY


def test_raising_needs_a_spec(db: Session) -> None:
    user = _person(db)
    agent = _agent(db, user, "Front desk")

    problems = _refused(lambda: _raise(db, user, agent, CHANGE))

    assert "Write its spec first" in problems[0]
    assert _count(db, agent) == 0


def test_raising_lists_every_problem_and_stores_nothing(db: Session) -> None:
    user, agent, _ = _ready(db)
    other = _agent(db, user, "Other line")
    _catalogue(db, other, "3")
    elsewhere = _call(db, other, _booking(1, FULL), days_ago=1, version=3)
    bad = QuestionDraft(
        question=" ",
        answers=[AnswerDraft("Yes", "")],
        category="no_such_category",
        call_ids=[elsewhere],
        replaces_key="no_such_rule",
    )
    same_labels = CHANGE._replace(
        question="Another question",
        answers=[AnswerDraft("Yes", "A rule"), AnswerDraft("yes!", "Another rule")],
    )

    problems = _refused(lambda: _raise(db, user, agent, bad, same_labels, CHANGE))

    joined = " | ".join(problems)
    for expected in (
        "Question 1: the question is empty",
        "Question 1: give two to four answers, not 1",
        "Question 1, answer a: write the rule this answer becomes",
        "Question 1: unknown category 'no_such_category'",
        "Question 1: 1 of its calls are not this agent's",
        "Question 1: the rule 'no_such_rule' it replaces is not in the agent's spec",
        "Question 2, answer b: the same label as another answer",
    ):
        assert expected in joined
    assert "Question 3" not in joined
    assert _count(db, agent) == 0


def test_the_same_question_is_not_raised_twice(db: Session) -> None:
    user, agent, _ = _ready(db)
    [change] = _raise(db, user, agent, CHANGE)
    reworded = CHANGE._replace(question=CHANGE.question.upper().replace("?", "!"))

    problems = _refused(lambda: _raise(db, user, agent, reworded))
    assert "already open or parked" in problems[0]
    twice = _refused(lambda: _raise(db, user, agent, DEPOSIT, DEPOSIT))
    assert "Question 2: the same question is already open" in twice[0]

    # Once answered, the same question may be asked again.
    _answer(db, user, (change.id, "b"))
    assert len(_raise(db, user, agent, CHANGE)) == 1


def test_answers_for_one_agent_make_one_spec_version(db: Session) -> None:
    user, agent, calls = _ready(db)
    before = crud.latest_spec(session=db, agent_id=agent.id)
    assert before is not None
    change, deposit = _raise(db, user, agent, CHANGE._replace(call_ids=calls), DEPOSIT)

    result = _answer(db, user, (change.id, " B"), (deposit.id, "b"))

    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    assert (spec.version, spec.origin) == (before.version + 1, SpecOrigin.ANSWERED)
    assert (spec.created_by, spec.assistant_name) == (user.id, ASSISTANT)
    assert spec.agent_version == before.agent_version
    assert isinstance(result, AnswerResult)
    assert (result.specs, result.answered, result.parked) == ({agent.id: spec}, 2, 0)
    rules = _rules(db, spec)
    assert len(rules) == len(RULES) + 2
    answered = {r.text: r for r in rules if r.source is SpecRuleSource.CLARIFICATION}
    assert set(answered) == {
        "Change an existing appointment only when the caller asks for it",
        "Never mention a deposit",
    }
    assert answered["Never mention a deposit"].touches is SpecRuleTouches.MONEY
    assert answered["Never mention a deposit"].clarification_id == deposit.id
    db.refresh(change)
    assert (change.state, change.answer, change.answer_spec_id) == (
        ClarificationState.ANSWERED,
        "b",
        spec.id,
    )
    assert (change.decided_by, change.decided_assistant) == (user.id, ASSISTANT)
    # The earlier version is untouched.
    assert len(_rules(db, before)) == len(RULES)
    # Answering is not reviewing: the spec stays current, as it was.
    assert spec_state(spec, "7") == "current"


def test_an_answer_is_final(db: Session) -> None:
    user, agent, _ = _ready(db)
    [change] = _raise(db, user, agent, CHANGE)
    _answer(db, user, (change.id, "c"))
    versions = crud.latest_spec(session=db, agent_id=agent.id)

    problems = _refused(lambda: _answer(db, user, (change.id, "a")))

    assert "already answered (c)" in problems[0]
    assert crud.latest_spec(session=db, agent_id=agent.id) == versions


def test_a_replacing_answer_takes_the_old_rules_key(db: Session) -> None:
    user, agent, _ = _ready(db)
    [change] = _raise(db, user, agent, CHANGE)
    _answer(db, user, (change.id, "c"))
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    old = next(r for r in _rules(db, spec) if r.clarification_id == change.id)
    again = CHANGE._replace(
        question="The new prompt lets callers move appointments. Change the answer?",
        replaces_key=old.key,
    )
    [replacing] = _raise(db, user, agent, again)

    _answer(db, user, (replacing.id, "b"))

    newest = crud.latest_spec(session=db, agent_id=agent.id)
    assert newest is not None
    rules = {r.key: r for r in _rules(db, newest)}
    assert len(rules) == len(RULES) + 1
    assert rules[old.key].text == (
        "Change an existing appointment only when the caller asks for it"
    )
    assert (rules[old.key].clarification_id, rules[old.key].position) == (
        replacing.id,
        old.position,
    )


def test_one_rule_is_replaced_by_one_question_at_a_time(db: Session) -> None:
    user, agent, _ = _ready(db)
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    key = _rules(db, spec)[0].key
    _raise(db, user, agent, CHANGE._replace(replaces_key=key))

    problems = _refused(
        lambda: _raise(db, user, agent, DEPOSIT._replace(replaces_key=key))
    )

    assert f"already replaces rule '{key}'" in problems[0]


def test_parking_makes_no_version_and_a_parked_question_can_be_answered(
    db: Session,
) -> None:
    user, agent, _ = _ready(db)
    [change] = _raise(db, user, agent, CHANGE)
    before = crud.latest_spec(session=db, agent_id=agent.id)

    _answer(db, user, (change.id, "park"))

    db.refresh(change)
    assert change.state is ClarificationState.PARKED
    assert crud.latest_spec(session=db, agent_id=agent.id) == before
    assert (
        "already parked" in _refused(lambda: _answer(db, user, (change.id, "park")))[0]
    )
    _answer(db, user, (change.id, "a"))
    db.refresh(change)
    assert change.state is ClarificationState.ANSWERED


def test_every_answer_and_park_is_a_decision_record(db: Session) -> None:
    user, agent, _ = _ready(db)
    change, deposit = _raise(db, user, agent, CHANGE, DEPOSIT)

    _answer(db, user, (change.id, "b"), (deposit.id, "park"))

    records = db.exec(
        select(DecisionRecord)
        .where(DecisionRecord.agent_id == agent.id)
        .order_by(col(DecisionRecord.kind))
    ).all()
    assert [(r.kind, r.subject, r.old_value, r.new_value) for r in records] == [
        (DecisionKind.CLARIFICATION_ANSWERED, str(change.id), "open", "b"),
        (DecisionKind.CLARIFICATION_PARKED, str(deposit.id), "open", "parked"),
    ]
    answered = records[0]
    assert answered.assistant_name == ASSISTANT
    assert answered.detail == {
        "rule": "Change an existing appointment only when the caller asks for it",
        "spec_version": 2,
    }


def test_answering_lists_every_problem_and_stores_nothing(db: Session) -> None:
    user, agent, _ = _ready(db)
    change, deposit = _raise(db, user, agent, CHANGE, DEPOSIT)
    stranger = _person(db)

    problems = _refused(
        lambda: _answer(
            db,
            user,
            (change.id, "b"),
            (change.id, "c"),
            (deposit.id, "c"),  # it has two answers
            (uuid.uuid4(), "a"),
        )
    )

    assert problems[0] == "Answer 2: the same clarification is given twice."
    assert problems[1] == (
        "Answer 3: answer with one of a, b, 'other' with text, 'park', or 'reopen' for a parked question."
    )
    assert problems[2].startswith("Answer 4: no clarification")
    db.refresh(change)
    assert change.state is ClarificationState.OPEN
    # Another workspace's clarifications are not found.
    assert (
        "no clarification"
        in _refused(lambda: _answer(db, stranger, (change.id, "a")))[0]
    )


def test_write_spec_carries_answered_rules_and_refuses_them(db: Session) -> None:
    user, agent, _ = _ready(db)
    [change] = _raise(db, user, agent, CHANGE)
    _answer(db, user, (change.id, "c"))
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    answered = next(r for r in _rules(db, spec) if r.clarification_id == change.id)

    with pytest.raises(SpecRefused) as refused:
        write_agent_spec(
            session=db,
            agent=agent,
            drafts=[RULES[0]._replace(key=answered.key)],
            author=user,
            assistant_name=ASSISTANT,
        )
    assert "a rule from the person's answer" in refused.value.problems[0]

    written = write_agent_spec(
        session=db, agent=agent, drafts=RULES[:1], author=user, assistant_name=ASSISTANT
    )

    assert (written.changes.carried, written.changes.dropped) == (1, 2)
    newest = crud.latest_spec(session=db, agent_id=agent.id)
    assert newest is not None
    carried = next(r for r in _rules(db, newest) if r.key == answered.key)
    assert (carried.text, carried.clarification_id, carried.source) == (
        answered.text,
        change.id,
        SpecRuleSource.CLARIFICATION,
    )


def test_an_answer_on_an_adopted_spec_still_needs_review(db: Session) -> None:
    user, agent, _ = _ready(db, version=7)
    _catalogue(db, agent, "8")
    _call(db, agent, _booking(1, FULL), days_ago=0, version=8)
    adopt_spec_safely(session=db, agent_id=agent.id)
    [change] = _raise(db, user, agent, CHANGE)

    _answer(db, user, (change.id, "b"))

    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    assert (spec.origin, spec.agent_version, spec.written_for) == (
        SpecOrigin.ANSWERED,
        "8",
        "7",
    )
    assert spec_state(spec, "8") == "needs_review"
    # The adopted rules and the answer are all there.
    assert len(_rules(db, spec)) == len(RULES) + 1


def test_open_counts_stay_in_their_workspace(db: Session) -> None:
    user, agent, _ = _ready(db)
    other_user, other_agent, _ = _ready(db)
    change, _deposit = _raise(db, user, agent, CHANGE, DEPOSIT)
    _raise(db, other_user, other_agent, CHANGE)
    _answer(db, user, (change.id, "park"))

    assert open_counts(session=db, company_id=user.company_id) == {agent.id: 1}
    assert state_counts(session=db, company_id=user.company_id) == {
        ClarificationState.OPEN: 1,
        ClarificationState.ANSWERED: 0,
        ClarificationState.PARKED: 1,
    }
    assert (
        state_counts(
            session=db, company_id=other_user.company_id, agent_id=other_agent.id
        )[ClarificationState.OPEN]
        == 1
    )


def test_a_replaced_rule_dropped_since_is_not_brought_back(db: Session) -> None:
    user, agent, _ = _ready(db)
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    dropped = next(r for r in _rules(db, spec) if r.text == RULES[1].text)
    [change] = _raise(db, user, agent, CHANGE._replace(replaces_key=dropped.key))
    write_agent_spec(
        session=db, agent=agent, drafts=RULES[:1], author=user, assistant_name=ASSISTANT
    )

    _answer(db, user, (change.id, "c"))

    newest = crud.latest_spec(session=db, agent_id=agent.id)
    assert newest is not None
    rules = _rules(db, newest)
    assert dropped.key not in {r.key for r in rules}
    assert any(r.clarification_id == change.id for r in rules)


def test_a_parked_question_can_be_reopened_and_only_then(db: Session) -> None:
    user, agent, _ = _ready(db)
    change, deposit = _raise(db, user, agent, CHANGE, DEPOSIT)
    _answer(db, user, (change.id, "park"))

    _answer(db, user, (change.id, "reopen"))

    db.refresh(change)
    assert change.state is ClarificationState.OPEN
    assert (
        "only a parked question"
        in _refused(lambda: _answer(db, user, (deposit.id, "reopen")))[0]
    )
    record = db.exec(
        select(DecisionRecord).where(
            DecisionRecord.agent_id == agent.id,
            DecisionRecord.kind == DecisionKind.CLARIFICATION_REOPENED,
        )
    ).one()
    assert (record.subject, record.old_value, record.new_value) == (
        str(change.id),
        "parked",
        "open",
    )


def test_open_questions_come_most_important_first(db: Session) -> None:
    user, agent, calls = _ready(db)
    plain, money, seen = _raise(
        db,
        user,
        agent,
        CHANGE._replace(question="A plain question?"),
        DEPOSIT,
        CHANGE._replace(question="Seen on calls?", call_ids=calls),
    )

    rows, more = list_page(
        session=db,
        company_id=user.company_id,
        state=ClarificationState.OPEN,
        agent_id=agent.id,
        offset=0,
        limit=10,
    )

    assert [r.id for r in rows] == [seen.id, money.id, plain.id]
    assert more is False


def test_an_answer_in_the_app_names_no_assistant(db: Session) -> None:
    user, agent, _ = _ready(db)
    [change] = _raise(db, user, agent, CHANGE)

    # The person answers in the app: no assistant acted for them.
    answer_clarifications(
        session=db,
        company_id=user.company_id,
        decisions=[Decision(change.id, "c")],
        decided_by=user,
        assistant_name=None,
    )

    db.refresh(change)
    assert change.decided_assistant is None
    record = db.exec(
        select(DecisionRecord).where(
            DecisionRecord.subject == str(change.id),
            DecisionRecord.kind == DecisionKind.CLARIFICATION_ANSWERED,
        )
    ).one()
    assert record.assistant_name is None
    assert record.detail is not None and set(record.detail) == {"rule", "spec_version"}
