"""Raising, answering and parking clarifications (plan
`plans/2026-11-15-clarifications.md`).

A clarification is a question about behaviour an agent's spec does not settle, with two
to four answers, each carrying the rule it becomes. Answers for one agent, given
together, make one new spec version. Everything here is all or nothing: every problem
is listed and nothing is stored unless all of it is right.
"""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from typing import NamedTuple

from sqlmodel import Session

from app import crud
from app.crud.check import lock_agent
from app.crud.clarification import (
    Answer,
    agent_call_ids,
    decide,
    get_clarifications,
    unanswered,
    write_answered_spec,
)
from app.crud.spec import normalise
from app.models.agent import Agent
from app.models.clarification import ANSWER_LETTERS, Clarification
from app.models.enums import ClarificationState, SpecRuleTouches
from app.models.spec import Spec
from app.models.user import User
from app.services.spec import MAX_RULE_LENGTH

MAX_QUESTIONS = 20
MAX_QUESTION_LENGTH = 500
MAX_LABEL_LENGTH = 100
MAX_CALLS = 50
PARK = "park"


class ClarificationRefused(Exception):
    def __init__(self, error: str, problems: list[str]) -> None:
        super().__init__(error)
        self.error = error
        self.problems = problems


class AnswerDraft(NamedTuple):
    label: str
    rule: str


class QuestionDraft(NamedTuple):
    question: str
    answers: Sequence[AnswerDraft]
    category: str
    touches: SpecRuleTouches | None = None
    call_ids: Sequence[uuid.UUID] = ()
    replaces_key: str | None = None


def _check_question(
    n: int,
    draft: QuestionDraft,
    *,
    categories: set[str],
    rule_keys: set[str],
) -> list[str]:
    q = f"Question {n}"
    problems: list[str] = []
    if not draft.question.strip():
        problems.append(f"{q}: the question is empty.")
    elif len(draft.question) > MAX_QUESTION_LENGTH:
        problems.append(f"{q}: longer than {MAX_QUESTION_LENGTH} characters.")
    if not 2 <= len(draft.answers) <= len(ANSWER_LETTERS):
        problems.append(f"{q}: give two to four answers, not {len(draft.answers)}.")
    labels: set[str] = set()
    for letter, answer in zip(ANSWER_LETTERS, draft.answers, strict=False):
        a = f"{q}, answer {letter}"
        label = normalise(answer.label)
        if not label:
            problems.append(f"{a}: the label is empty.")
        elif len(answer.label) > MAX_LABEL_LENGTH:
            problems.append(
                f"{a}: the label is longer than {MAX_LABEL_LENGTH} characters."
            )
        elif label in labels:
            problems.append(f"{a}: the same label as another answer.")
        labels.add(label)
        if not answer.rule.strip():
            problems.append(
                f"{a}: write the rule this answer becomes; every answer is a rule."
            )
        elif len(answer.rule) > MAX_RULE_LENGTH:
            problems.append(
                f"{a}: the rule is longer than {MAX_RULE_LENGTH} characters."
            )
    if draft.category not in categories:
        problems.append(
            f"{q}: unknown category '{draft.category}'; use a key from "
            "`list_categories`."
        )
    if len(set(draft.call_ids)) > MAX_CALLS:
        problems.append(f"{q}: at most {MAX_CALLS} calls.")
    if draft.replaces_key is not None and draft.replaces_key not in rule_keys:
        problems.append(
            f"{q}: the rule '{draft.replaces_key}' it replaces is not in the agent's "
            "spec."
        )
    return problems


def raise_clarifications(
    *,
    session: Session,
    agent: Agent,
    drafts: Sequence[QuestionDraft],
    raised_by: User,
    assistant_name: str | None,
) -> list[Clarification]:
    """Store ``drafts`` as open clarifications on the agent. Commits.

    Raises:
        ClarificationRefused: The agent has no spec, or a question is not right; every
            problem is listed and nothing is stored.
    """
    if not drafts:
        raise ClarificationRefused("Give at least one question", [])
    if len(drafts) > MAX_QUESTIONS:
        raise ClarificationRefused(f"At most {MAX_QUESTIONS} questions at a time", [])
    # Raised in turn per agent, so the same question asked twice at once is caught.
    lock_agent(session=session, agent_id=agent.id)
    spec = crud.latest_spec(session=session, agent_id=agent.id)
    if spec is None:
        session.rollback()
        raise ClarificationRefused(
            "The agent has no spec yet",
            [
                "Write its spec first: a clarification asks what the spec leaves unsettled."
            ],
        )
    categories = {c.key: c.id for c in crud.list_categories(session=session)}
    rule_keys = {r.key for r in crud.spec_rules(session=session, spec_id=spec.id)}
    waiting = unanswered(session=session, agent_id=agent.id)
    asked = {c.question_key for c in waiting}
    replacing = {c.replaces_key for c in waiting if c.replaces_key}
    calls = agent_call_ids(
        session=session,
        agent_id=agent.id,
        call_ids=[i for d in drafts for i in d.call_ids],
    )

    problems: list[str] = []
    for n, draft in enumerate(drafts, start=1):
        problems += _check_question(
            n, draft, categories=set(categories), rule_keys=rule_keys
        )
        key = normalise(draft.question)
        if key and key in asked:
            problems.append(
                f"Question {n}: the same question is already open or parked on this "
                "agent."
            )
        asked.add(key)
        if draft.replaces_key and draft.replaces_key in replacing:
            problems.append(
                f"Question {n}: another open or parked question already replaces rule "
                f"'{draft.replaces_key}'."
            )
        if draft.replaces_key:
            replacing.add(draft.replaces_key)
        foreign = set(draft.call_ids) - calls
        if foreign:
            problems.append(
                f"Question {n}: {len(foreign)} of its calls are not this agent's: "
                f"{', '.join(sorted(str(i) for i in foreign)[:5])}."
            )
    if problems:
        session.rollback()
        raise ClarificationRefused("The questions were not stored", problems)

    stored = []
    for draft in drafts:
        clarification = Clarification(
            company_id=agent.company_id,
            agent_id=agent.id,
            spec_id=spec.id,
            question=draft.question.strip(),
            question_key=normalise(draft.question),
            answers=[
                {"label": a.label.strip(), "rule": a.rule.strip()}
                for a in draft.answers
            ],
            category_id=categories[draft.category],
            touches=draft.touches,
            call_ids=[str(i) for i in dict.fromkeys(draft.call_ids)],
            replaces_key=draft.replaces_key,
            raised_by=raised_by.id,
            raised_by_email=raised_by.email,
            raised_assistant=assistant_name,
        )
        session.add(clarification)
        stored.append(clarification)
    session.commit()
    for clarification in stored:
        session.refresh(clarification)
    return stored


class Decision(NamedTuple):
    clarification_id: uuid.UUID
    # "a" to "d", or "park".
    answer: str


class AnswerResult(NamedTuple):
    # The new spec version per agent that had answers.
    specs: dict[uuid.UUID, Spec]
    answered: int
    parked: int


def answer_clarifications(
    *,
    session: Session,
    company_id: uuid.UUID,
    decisions: Sequence[Decision],
    decided_by: User,
    assistant_name: str | None,
) -> AnswerResult:
    """Answer or park clarifications in the workspace. Commits.

    The answers for one agent make one new spec version. Each answer and each park is a
    decision record.

    Raises:
        ClarificationRefused: A clarification is unknown, already answered or given
            twice, or an answer is not a to d or "park"; every problem is listed and
            nothing is stored.
    """
    if not decisions:
        raise ClarificationRefused("Give at least one answer", [])
    decisions = [d._replace(answer=d.answer.strip().lower()) for d in decisions]
    ids = [d.clarification_id for d in decisions]
    # Lock the agents first, then the clarifications, always in id order, so two
    # batches on the same agents wait for each other instead of deadlocking.
    first_look = get_clarifications(session=session, company_id=company_id, ids=ids)
    for agent_id in sorted({c.agent_id for c in first_look.values()}):
        lock_agent(session=session, agent_id=agent_id)
    found = get_clarifications(
        session=session, company_id=company_id, ids=ids, lock=True
    )

    problems: list[str] = []
    seen: set[uuid.UUID] = set()
    replacing: dict[tuple[uuid.UUID, str], int] = {}
    for n, decision in enumerate(decisions, start=1):
        d = f"Answer {n}"
        c = found.get(decision.clarification_id)
        if decision.clarification_id in seen:
            problems.append(f"{d}: the same clarification is given twice.")
            continue
        seen.add(decision.clarification_id)
        if c is None:
            problems.append(f"{d}: no clarification {decision.clarification_id}.")
            continue
        if c.state is ClarificationState.ANSWERED:
            problems.append(
                f"{d}: already answered ({c.answer}). An answer is final; to change "
                "it, raise a clarification that replaces its rule."
            )
            continue
        if decision.answer == PARK:
            if c.state is ClarificationState.PARKED:
                problems.append(f"{d}: already parked.")
            continue
        letters = ANSWER_LETTERS[: len(c.answers)]
        if decision.answer not in letters:
            problems.append(
                f"{d}: answer with one of {', '.join(letters)}, or '{PARK}'."
            )
            continue
        if c.replaces_key:
            slot = (c.agent_id, c.replaces_key)
            if slot in replacing:
                problems.append(
                    f"{d}: answer {replacing[slot]} replaces the same rule "
                    f"'{c.replaces_key}'."
                )
            replacing[slot] = n
    if problems:
        session.rollback()
        raise ClarificationRefused("Nothing was answered", problems)

    by_agent: dict[uuid.UUID, list[Answer]] = defaultdict(list)
    parks: list[Clarification] = []
    for decision in decisions:
        c = found[decision.clarification_id]
        if decision.answer == PARK:
            parks.append(c)
        else:
            by_agent[c.agent_id].append(Answer(c, decision.answer))

    specs: dict[uuid.UUID, Spec] = {}
    for agent_id, answers in by_agent.items():
        agent = session.get(Agent, agent_id)
        assert agent is not None  # the clarification's agent, locked above
        spec = write_answered_spec(
            session=session,
            agent=agent,
            answers=answers,
            decided_by=decided_by,
            assistant_name=assistant_name,
        )
        specs[agent_id] = spec
        for answer in answers:
            decide(
                session=session,
                clarification=answer.clarification,
                state=ClarificationState.ANSWERED,
                letter=answer.letter,
                answer_spec=spec,
                decided_by=decided_by,
                assistant_name=assistant_name,
            )
    for c in parks:
        decide(
            session=session,
            clarification=c,
            state=ClarificationState.PARKED,
            letter=None,
            answer_spec=None,
            decided_by=decided_by,
            assistant_name=assistant_name,
        )
    session.commit()
    for spec in specs.values():
        session.refresh(spec)
    return AnswerResult(
        specs=specs,
        answered=sum(len(a) for a in by_agent.values()),
        parked=len(parks),
    )
