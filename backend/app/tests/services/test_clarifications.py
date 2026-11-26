"""Raising, answering and parking questions: clarifications attached to a rule, and
prompt gaps for behaviour no rule covers, on invented agents and calls (plans
`plans/2026-11-15-clarifications.md`, `plans/2026-11-26-clarification-on-rule.md`)."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app import crud
from app.crud.clarification import (
    clarifications_in_force,
    list_page,
    open_counts,
    open_gaps,
    state_counts,
)
from app.crud.spec import copy_rule
from app.models import Agent, Spec, SpecRule, User
from app.models.check import DecisionRecord
from app.models.clarification import Clarification
from app.models.enums import (
    ClarificationState,
    DecisionKind,
    SpecOrigin,
    SpecRuleSource,
    SpecRuleTouches,
    TaskKind,
)
from app.services.clarification import (
    AnswerDraft,
    AnswerResult,
    ClarificationRefused,
    Decision,
    QuestionDraft,
    answer_clarifications,
    clarifications_public,
    raise_clarifications,
)
from app.services.rule_context import rules_with_clarifications
from app.services.spec import RuleDraft, SpecRefused, spec_answer, write_agent_spec
from app.services.work import work_list
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
# Behaviour no rule covers: prompt gaps.
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
    gap_topic="changing appointments",
    category="booking",
)
DEPOSIT = QuestionDraft(
    question="Callers asked about a deposit. May the agent say one is needed?",
    answers=[
        AnswerDraft("Yes", "Tell callers a deposit is needed for new patients"),
        AnswerDraft("No", "Never mention a deposit"),
    ],
    gap_topic="deposits",
    category="pricing_and_quotes",
    touches=SpecRuleTouches.MONEY,
)
# Where the opening-hours rule's boundary lies: a clarification. Its rule key is set
# per test, from the written spec.
HOURS = QuestionDraft(
    question="Callers asked for 8:00, the minute the clinic opens. Is that inside?",
    answers=[
        AnswerDraft(
            "Yes",
            "A slot that starts at opening time is inside opening hours; one that "
            "starts before it is not.",
        ),
        AnswerDraft(
            "No",
            "The first slot of the day starts 15 minutes after opening; an earlier one "
            "is outside opening hours.",
        ),
    ],
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


def _latest(db: Session, agent: Agent) -> Spec:
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    return spec


def _key(db: Session, agent: Agent, text: str = RULES[0].text) -> str:
    return next(r.key for r in _rules(db, _latest(db, agent)) if r.text == text)


def _count(db: Session, agent: Agent) -> int:
    return len(
        db.exec(select(Clarification).where(Clarification.agent_id == agent.id)).all()
    )


def _earlier_answer_rule(
    db: Session, user: User, agent: Agent, gap: Clarification, *, critical: bool
) -> SpecRule:
    """A rule as an answer made one before 2026-11-26: a spec version of origin
    `answered` with the answer as a rule pointing at its question."""
    previous = _latest(db, agent)
    spec = Spec(
        company_id=agent.company_id,
        agent_id=agent.id,
        version=previous.version + 1,
        agent_version=previous.agent_version,
        prompt_fingerprint=previous.prompt_fingerprint,
        origin=SpecOrigin.ANSWERED,
        written_for=previous.written_for,
        previous_id=previous.id,
        created_by=user.id,
        created_by_email=user.email,
    )
    db.add(spec)
    db.flush()
    for rule in _rules(db, previous):
        db.add(copy_rule(rule, spec_id=spec.id))
    rule = SpecRule(
        company_id=agent.company_id,
        spec_id=spec.id,
        key=uuid.uuid4().hex[:12],
        position=9,
        category_id=gap.category_id,
        text="Change an existing appointment only when the caller asks for it",
        source=SpecRuleSource.CLARIFICATION,
        clarification_id=gap.id,
        critical=critical,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def test_raising_stores_both_kinds_with_their_calls(db: Session) -> None:
    user, agent, calls = _ready(db)
    spec = _latest(db, agent)
    money_key = _key(db, agent, RULES[1].text)

    stored = _raise(
        db,
        user,
        agent,
        CHANGE._replace(call_ids=[*calls, calls[0]]),
        DEPOSIT,
        HOURS._replace(rule_key=money_key, category="booking"),
    )

    change, deposit, hours = stored
    assert change.state is ClarificationState.OPEN
    assert change.spec_id == spec.id
    assert change.call_ids == [str(c) for c in calls]  # duplicates dropped
    assert (change.rule_key, change.gap_topic) == (None, "changing appointments")
    assert [a["sentence"] for a in deposit.answers] == [
        "Tell callers a deposit is needed for new patients",
        "Never mention a deposit",
    ]
    assert (change.raised_by, change.raised_assistant) == (user.id, ASSISTANT)
    assert deposit.call_ids == []  # a question from a prompt change has no calls
    assert deposit.touches is SpecRuleTouches.MONEY
    # A clarification takes its rule's category and marker, not what was given.
    money_rule = next(r for r in _rules(db, spec) if r.key == money_key)
    assert (hours.rule_key, hours.gap_topic) == (money_key, None)
    assert (hours.category_id, hours.touches) == (
        money_rule.category_id,
        SpecRuleTouches.MONEY,
    )
    shown = clarifications_public(session=db, rows=stored)
    assert [q.kind for q in shown] == ["prompt_gap", "prompt_gap", "clarification"]
    assert shown[2].rule is not None and shown[2].rule.text == RULES[1].text


def test_raising_needs_a_spec(db: Session) -> None:
    user = _person(db)
    agent = _agent(db, user, "Front desk")

    problems = _refused(lambda: _raise(db, user, agent, CHANGE))

    assert "Write its spec first" in problems[0]
    assert _count(db, agent) == 0


def test_raising_lists_every_problem_and_stores_nothing(db: Session) -> None:
    user, agent, _ = _ready(db)
    key = _key(db, agent)
    other = _agent(db, user, "Other line")
    _catalogue(db, other, "3")
    elsewhere = _call(db, other, _booking(1, FULL), days_ago=1, version=3)
    bad = QuestionDraft(
        question=" ",
        answers=[AnswerDraft("Yes", "")],
        rule_key="no_such_rule",
        gap_topic="something",
        call_ids=[elsewhere],
    )
    same_labels = CHANGE._replace(
        question="Another question",
        answers=[AnswerDraft("Yes", "A rule"), AnswerDraft("yes!", "Another rule")],
    )
    no_topic = CHANGE._replace(
        question="A third question", gap_topic=None, category="no_such_category"
    )
    gap_replacing = DEPOSIT._replace(replaces_id=uuid.uuid4())
    not_in_force = HOURS._replace(rule_key=key, replaces_id=uuid.uuid4())

    problems = _refused(
        lambda: _raise(
            db, user, agent, bad, same_labels, no_topic, gap_replacing, not_in_force
        )
    )

    joined = " | ".join(problems)
    for expected in (
        "Question 1: the question is empty",
        "Question 1: give two to four answers, not 1",
        "Question 1, answer a: write the clarification it adds to the rule",
        "Question 1: 'no_such_rule' is not a rule of the agent's latest spec",
        "Question 1: `gap_topic` is only for a prompt gap",
        "Question 1: 1 of its calls are not this agent's",
        "Question 2, answer b: the same label as another answer",
        "Question 3: no `rule_key`, so it is a prompt gap",
        "Question 3: unknown category 'no_such_category'",
        "Question 4: only a clarification replaces another",
        "is not a clarification in force on rule",
    ):
        assert expected in joined
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


def test_a_clarification_is_attached_to_its_rule_and_makes_no_version(
    db: Session,
) -> None:
    user, agent, _ = _ready(db)
    before = _latest(db, agent)
    key = _key(db, agent)
    [hours] = _raise(db, user, agent, HOURS._replace(rule_key=key))

    result = _answer(db, user, (hours.id, " A"))

    assert isinstance(result, AnswerResult)
    assert (result.answered, result.clarifications, result.prompt_gaps) == (
        1,
        {agent.id: 1},
        {agent.id: 0},
    )
    # No rule and no spec version: the rule changes only with the prompt.
    assert _latest(db, agent).id == before.id
    assert len(_rules(db, before)) == len(RULES)
    db.refresh(hours)
    assert (hours.state, hours.answer, hours.answer_spec_id) == (
        ClarificationState.ANSWERED,
        "a",
        None,
    )
    in_force = clarifications_in_force(session=db, agent_id=agent.id)
    assert [c.id for c in in_force[key]] == [hours.id]

    answer = spec_answer(session=db, agent=agent)
    assert answer is not None and answer.counts is not None
    rule = next(r for g in answer.groups for r in g.rules if r.key == key)
    assert [c.sentence for c in rule.clarifications] == [str(HOURS.answers[0].sentence)]
    assert rule.clarifications[0].answer == "Yes"
    assert (answer.counts.clarified, answer.counts.prompt_gaps) == (1, 0)


def test_a_prompt_gap_answer_adds_no_rule_and_becomes_a_task(db: Session) -> None:
    user, agent, _ = _ready(db)
    before = _latest(db, agent)
    [change] = _raise(db, user, agent, CHANGE)

    result = _answer(db, user, (change.id, "b"))

    assert isinstance(result, AnswerResult)
    assert result.prompt_gaps == {agent.id: 1}
    assert _latest(db, agent).id == before.id
    assert [g.id for g in open_gaps(session=db, company_id=user.company_id)] == [
        change.id
    ]
    tasks = [
        t
        for t in work_list(session=db, company_id=user.company_id)
        if t.kind is TaskKind.PROMPT_GAP
    ]
    assert [(t.key, t.title, t.ref) for t in tasks] == [
        (
            f"prompt_gap:{change.id}",
            "Propose the prompt change: changing appointments",
            change.id,
        )
    ]
    answer = spec_answer(session=db, agent=agent)
    assert answer is not None and answer.counts is not None
    assert answer.counts.prompt_gaps == 1
    # Nothing checks it: no rule carries it.
    assert clarifications_in_force(session=db, agent_id=agent.id) == {}


def test_an_answer_is_final(db: Session) -> None:
    user, agent, _ = _ready(db)
    [change] = _raise(db, user, agent, CHANGE)
    _answer(db, user, (change.id, "c"))

    problems = _refused(lambda: _answer(db, user, (change.id, "a")))

    assert "already answered (c)" in problems[0]
    assert "`replaces_id`" in problems[0]


def test_a_replacing_question_replaces_the_earlier_clarification(db: Session) -> None:
    user, agent, _ = _ready(db)
    key = _key(db, agent)
    [first] = _raise(db, user, agent, HOURS._replace(rule_key=key))
    _answer(db, user, (first.id, "a"))
    again = HOURS._replace(
        question="Calls show 8:00 slots overbooking the first dentist. Change it?",
        rule_key=key,
        replaces_id=first.id,
    )
    [replacing] = _raise(db, user, agent, again)
    [shown] = clarifications_public(session=db, rows=[replacing])
    assert shown.replaces_sentence == HOURS.answers[0].sentence

    _answer(db, user, (replacing.id, "b"))

    in_force = clarifications_in_force(session=db, agent_id=agent.id)
    assert [c.id for c in in_force[key]] == [replacing.id]
    # The earlier one stays in the history, and can no longer be replaced.
    db.refresh(first)
    assert first.state is ClarificationState.ANSWERED
    problems = _refused(
        lambda: _raise(
            db,
            user,
            agent,
            HOURS._replace(question="Once more?", rule_key=key, replaces_id=first.id),
        )
    )
    assert "is not a clarification in force" in problems[0]


def test_one_clarification_is_replaced_by_one_question_at_a_time(db: Session) -> None:
    user, agent, _ = _ready(db)
    key = _key(db, agent)
    [first] = _raise(db, user, agent, HOURS._replace(rule_key=key))
    _answer(db, user, (first.id, "a"))
    _raise(
        db,
        user,
        agent,
        HOURS._replace(question="Replace it?", rule_key=key, replaces_id=first.id),
    )

    problems = _refused(
        lambda: _raise(
            db,
            user,
            agent,
            HOURS._replace(question="Or this?", rule_key=key, replaces_id=first.id),
        )
    )

    assert f"already replaces clarification {first.id}" in problems[0]


def test_parking_and_a_parked_question_can_be_answered(db: Session) -> None:
    user, agent, _ = _ready(db)
    [change] = _raise(db, user, agent, CHANGE)

    _answer(db, user, (change.id, "park"))

    db.refresh(change)
    assert change.state is ClarificationState.PARKED
    assert open_gaps(session=db, company_id=user.company_id) == []
    assert (
        "already parked" in _refused(lambda: _answer(db, user, (change.id, "park")))[0]
    )
    _answer(db, user, (change.id, "a"))
    db.refresh(change)
    assert change.state is ClarificationState.ANSWERED


def test_every_answer_and_park_is_a_decision_record(db: Session) -> None:
    user, agent, _ = _ready(db)
    key = _key(db, agent)
    change, deposit, hours = _raise(
        db, user, agent, CHANGE, DEPOSIT, HOURS._replace(rule_key=key)
    )

    _answer(db, user, (change.id, "b"), (deposit.id, "park"), (hours.id, "a"))

    records = {
        r.subject: r
        for r in db.exec(
            select(DecisionRecord).where(DecisionRecord.agent_id == agent.id)
        ).all()
        if r.kind
        in (DecisionKind.CLARIFICATION_ANSWERED, DecisionKind.CLARIFICATION_PARKED)
    }
    assert (records[str(deposit.id)].kind, records[str(deposit.id)].new_value) == (
        DecisionKind.CLARIFICATION_PARKED,
        "parked",
    )
    assert records[str(change.id)].assistant_name == ASSISTANT
    assert records[str(change.id)].detail == {
        "sentence": "Change an existing appointment only when the caller asks for it",
        "prompt_gap": True,
    }
    assert records[str(hours.id)].detail == {
        "sentence": HOURS.answers[0].sentence,
        "rule_key": key,
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


def test_clarifications_stay_with_their_key_and_changed_rules_list_them(
    db: Session,
) -> None:
    user, agent, _ = _ready(db)
    key = _key(db, agent)
    money = _key(db, agent, RULES[1].text)
    [hours] = _raise(db, user, agent, HOURS._replace(rule_key=key))
    _answer(db, user, (hours.id, "a"))

    # The prompt changed the rule's words: the clarification stays and is listed.
    written = write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(key=key, text="Never book outside the clinic's hours"),
            RULES[1]._replace(key=money),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )
    assert [
        (c.rule_key, c.clarification_id) for c in written.changes.check_clarifications
    ] == [(key, hours.id)]
    rule = next(r for g in written.groups for r in g.rules if r.key == key)
    assert [c.id for c in rule.clarifications] == [hours.id]

    # Dropped from the spec: it stops applying and stays in the history.
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[RULES[1]._replace(key=money)],
        author=user,
        assistant_name=ASSISTANT,
    )
    answer = spec_answer(session=db, agent=agent)
    assert answer is not None and answer.counts is not None
    assert answer.counts.clarified == 0
    rules = rules_with_clarifications(
        session=db, agent_id=agent.id, rules=_rules(db, _latest(db, agent))
    )
    assert key not in rules


def test_a_rule_written_from_the_new_prompt_closes_the_gap(db: Session) -> None:
    user, agent, _ = _ready(db)
    [change] = _raise(db, user, agent, CHANGE)
    _answer(db, user, (change.id, "b"))
    covering = RuleDraft(
        text="Change an existing appointment only when the caller asks for it",
        category="booking",
        quote="Only book within opening hours",
        touches=None,
        key=None,
        closes=[change.id],
    )

    with pytest.raises(SpecRefused) as refused:
        write_agent_spec(
            session=db,
            agent=agent,
            drafts=[
                *RULES,
                covering._replace(closes=[uuid.uuid4()]),
                covering._replace(text="Once more", closes=[change.id, change.id]),
            ],
            author=user,
            assistant_name=ASSISTANT,
        )
    joined = " | ".join(refused.value.problems)
    assert "is not an answered prompt gap of this agent" in joined
    assert "is already closed by rule 4" in joined

    written = write_agent_spec(
        session=db,
        agent=agent,
        drafts=[*RULES, covering],
        author=user,
        assistant_name=ASSISTANT,
    )

    assert written.changes.gaps_closed == 1
    db.refresh(change)
    spec = _latest(db, agent)
    assert change.closed_spec_id == spec.id and change.closed_at is not None
    assert change.closed_rule_key in {r.key for r in _rules(db, spec)}
    assert open_gaps(session=db, company_id=user.company_id) == []
    assert not any(
        t.kind is TaskKind.PROMPT_GAP
        for t in work_list(session=db, company_id=user.company_id)
    )
    closed = db.exec(
        select(DecisionRecord).where(
            DecisionRecord.agent_id == agent.id,
            DecisionRecord.kind == DecisionKind.PROMPT_GAP_CLOSED,
        )
    ).one()
    assert (closed.subject, closed.new_value) == (
        str(change.id),
        change.closed_rule_key,
    )


def test_a_rule_from_an_earlier_answer_is_carried_until_its_gap_closes(
    db: Session,
) -> None:
    user, agent, _ = _ready(db)
    [change] = _raise(db, user, agent, CHANGE)
    _answer(db, user, (change.id, "b"))
    old = _earlier_answer_rule(db, user, agent, change, critical=True)
    answer = spec_answer(session=db, agent=agent)
    assert answer is not None and answer.counts is not None
    shown = next(r for g in answer.groups for r in g.rules if r.key == old.key)
    assert shown.prompt_gap_id == change.id
    assert (answer.counts.from_answers, answer.counts.prompt_gaps) == (1, 1)

    # Not yet in the prompt: carried over unchanged, and its key is not the writer's.
    written = write_agent_spec(
        session=db, agent=agent, drafts=RULES, author=user, assistant_name=ASSISTANT
    )
    assert written.changes.carried == 1
    with pytest.raises(SpecRefused) as refused:
        write_agent_spec(
            session=db,
            agent=agent,
            drafts=[*RULES, RULES[0]._replace(text="Changing", key=old.key)],
            author=user,
            assistant_name=ASSISTANT,
        )
    assert "is a rule from an earlier answer" in refused.value.problems[0]

    # The prompt now says it: the closing rule takes the old key and its critical mark.
    closed = write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            *RULES,
            RuleDraft(
                text="Change an appointment only when the caller asks",
                category="booking",
                quote="Only book within opening hours",
                touches=None,
                key=None,
                closes=[change.id],
            ),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )

    assert (closed.changes.carried, closed.changes.gaps_closed) == (0, 1)
    rules = {r.key: r for r in _rules(db, _latest(db, agent))}
    assert rules[old.key].source is SpecRuleSource.PROMPT
    assert rules[old.key].critical is True
    assert rules[old.key].text == "Change an appointment only when the caller asks"
    assert not any(r.source is SpecRuleSource.CLARIFICATION for r in rules.values())


def test_in_force_reads_what_was_answered_by_then(db: Session) -> None:
    user, agent, _ = _ready(db)
    key = _key(db, agent)
    before = datetime.now(UTC)
    [hours] = _raise(db, user, agent, HOURS._replace(rule_key=key))
    _answer(db, user, (hours.id, "a"))
    rules = _rules(db, _latest(db, agent))

    then = rules_with_clarifications(
        session=db, agent_id=agent.id, rules=rules, at=before - timedelta(seconds=1)
    )
    now = rules_with_clarifications(session=db, agent_id=agent.id, rules=rules)

    assert then[key].clarifications == ()
    assert now[key].clarification_ids == [str(hours.id)]
    assert now[key].fingerprint != then[key].fingerprint
    # A rule with no clarification answers the same fingerprint at any time.
    other = next(r.key for r in rules if r.key != key)
    assert now[other].fingerprint == then[other].fingerprint


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
    assert record.detail is not None and set(record.detail) == {
        "sentence",
        "prompt_gap",
    }
