"""Raising, answering and parking questions for the person (plans
`plans/2026-11-15-clarifications.md`, `plans/2026-11-26-clarification-on-rule.md`).

A question either explains an existing spec rule (a clarification, with ``rule_key``)
or asks about behaviour no rule covers (a prompt gap, with ``gap_topic``). Each has two
to four answers, each with the sentence it adds. An answer never writes a rule or a
spec version: a clarification is read with its rule by every check, and a prompt gap
becomes a task to propose the prompt change. Everything here is all or nothing: every
problem is listed and nothing is stored unless all of it is right.
"""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from sqlmodel import Session, col, select

from app import crud
from app.crud.check import lock_agent
from app.crud.clarification import (
    Answer,
    agent_call_ids,
    answered_since,
    chosen_sentence,
    clarifications_in_force,
    decide,
    get_clarifications,
    state_counts,
    unanswered,
)
from app.crud.spec import normalise
from app.models.agent import Agent
from app.models.clarification import (
    ANSWER_LETTERS,
    OTHER,
    AnsweredAgentPublic,
    Clarification,
    ClarificationAnswerPublic,
    ClarificationCountsPublic,
    ClarificationPublic,
    ClarificationsAnsweredPublic,
    ClarifiedRulePublic,
)
from app.models.enums import ClarificationState, SpecRuleTouches
from app.models.spec import Spec
from app.models.user import User
from app.services.spec import MAX_RULE_LENGTH

MAX_QUESTIONS = 20
MAX_QUESTION_LENGTH = 500
MAX_LABEL_LENGTH = 100
MAX_TOPIC_LENGTH = 100
MAX_CALLS = 50
PARK = "park"
MAX_OTHER_LENGTH = 500
REOPEN = "reopen"


class ClarificationRefused(Exception):
    def __init__(self, error: str, problems: list[str]) -> None:
        super().__init__(error)
        self.error = error
        self.problems = problems


class AnswerDraft(NamedTuple):
    label: str
    sentence: str


class QuestionDraft(NamedTuple):
    question: str
    answers: Sequence[AnswerDraft]
    # The rule it explains; none for a prompt gap.
    rule_key: str | None = None
    # For a prompt gap: the behaviour in a few words, and its category.
    gap_topic: str | None = None
    category: str | None = None
    touches: SpecRuleTouches | None = None
    call_ids: Sequence[uuid.UUID] = ()
    # An answered clarification on the same rule that this question's answer replaces.
    replaces_id: uuid.UUID | None = None


def _check_question(
    n: int,
    draft: QuestionDraft,
    *,
    categories: set[str],
    rule_keys: set[str],
    in_force: dict[uuid.UUID, str],
) -> list[str]:
    q = f"Question {n}"
    problems: list[str] = []
    if not draft.question.strip():
        problems.append(f"{q}: the question is empty.")
    elif len(draft.question) > MAX_QUESTION_LENGTH:
        problems.append(f"{q}: longer than {MAX_QUESTION_LENGTH} characters.")
    if not 2 <= len(draft.answers) <= len(ANSWER_LETTERS):
        problems.append(f"{q}: give two to four answers, not {len(draft.answers)}.")
    what = "clarification it adds to the rule" if draft.rule_key else "prompt sentence"
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
        if not answer.sentence.strip():
            problems.append(f"{a}: write the {what}; every answer adds one sentence.")
        elif len(answer.sentence) > MAX_RULE_LENGTH:
            problems.append(
                f"{a}: the sentence is longer than {MAX_RULE_LENGTH} characters."
            )
    if draft.rule_key is not None:
        if draft.rule_key not in rule_keys:
            problems.append(
                f"{q}: '{draft.rule_key}' is not a rule of the agent's latest spec; use "
                "a key from `get_spec`, or leave `rule_key` out for behaviour no rule "
                "covers (a prompt gap)."
            )
        if draft.gap_topic:
            problems.append(
                f"{q}: `gap_topic` is only for a prompt gap; a question about rule "
                f"'{draft.rule_key}' takes the rule's category."
            )
    else:
        topic = (draft.gap_topic or "").strip()
        if not topic:
            problems.append(
                f"{q}: no `rule_key`, so it is a prompt gap: name the behaviour in a "
                "few words as `gap_topic`, or give the key of the rule it explains."
            )
        elif len(topic) > MAX_TOPIC_LENGTH:
            problems.append(f"{q}: `gap_topic` is longer than {MAX_TOPIC_LENGTH}.")
        if draft.category not in categories:
            problems.append(
                f"{q}: unknown category '{draft.category}'; a prompt gap needs a key "
                "from `list_categories`."
            )
        if draft.replaces_id is not None:
            problems.append(
                f"{q}: only a clarification replaces another; give its `rule_key`."
            )
    if len(set(draft.call_ids)) > MAX_CALLS:
        problems.append(f"{q}: at most {MAX_CALLS} calls.")
    if (
        draft.replaces_id is not None
        and draft.rule_key is not None
        and in_force.get(draft.replaces_id) != draft.rule_key
    ):
        problems.append(
            f"{q}: {draft.replaces_id} is not a clarification in force on rule "
            f"'{draft.rule_key}'; `get_spec` lists each rule's clarifications."
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
    rules = {r.key: r for r in crud.spec_rules(session=session, spec_id=spec.id)}
    in_force = {
        c.id: key
        for key, rows in clarifications_in_force(
            session=session, agent_id=agent.id
        ).items()
        for c in rows
    }
    waiting = unanswered(session=session, agent_id=agent.id)
    asked = {c.question_key for c in waiting}
    replacing = {c.replaces_id for c in waiting if c.replaces_id}
    calls = agent_call_ids(
        session=session,
        agent_id=agent.id,
        call_ids=[i for d in drafts for i in d.call_ids],
    )

    problems: list[str] = []
    for n, draft in enumerate(drafts, start=1):
        problems += _check_question(
            n,
            draft,
            categories=set(categories),
            rule_keys=set(rules),
            in_force=in_force,
        )
        key = normalise(draft.question)
        if key and key in asked:
            problems.append(
                f"Question {n}: the same question is already open or parked on this "
                "agent."
            )
        asked.add(key)
        if draft.replaces_id and draft.replaces_id in replacing:
            problems.append(
                f"Question {n}: another open or parked question already replaces "
                f"clarification {draft.replaces_id}."
            )
        if draft.replaces_id:
            replacing.add(draft.replaces_id)
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
        rule = rules.get(draft.rule_key) if draft.rule_key else None
        clarification = Clarification(
            company_id=agent.company_id,
            agent_id=agent.id,
            spec_id=spec.id,
            question=draft.question.strip(),
            question_key=normalise(draft.question),
            answers=[
                {"label": a.label.strip(), "sentence": a.sentence.strip()}
                for a in draft.answers
            ],
            rule_key=draft.rule_key,
            gap_topic=None if rule else (draft.gap_topic or "").strip(),
            # A clarification takes its rule's category and marker.
            category_id=rule.category_id if rule else categories[draft.category or ""],
            touches=rule.touches if rule else draft.touches,
            call_ids=[str(i) for i in dict.fromkeys(draft.call_ids)],
            replaces_id=draft.replaces_id,
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
    # "a" to "d", "other" with ``text``, "park", or "reopen" for a parked one.
    answer: str
    # For "other": the person's own words, kept as the sentence.
    text: str | None = None
    # The assistant proposed this answer and the person confirmed it.
    proposed: bool = False


class AnswerResult(NamedTuple):
    answered: int
    parked: int
    # Per agent with answers: clarifications added to rules, and prompt gaps answered.
    clarifications: dict[uuid.UUID, int]
    prompt_gaps: dict[uuid.UUID, int]
    reopened: int = 0


def answer_clarifications(
    *,
    session: Session,
    company_id: uuid.UUID,
    decisions: Sequence[Decision],
    decided_by: User,
    assistant_name: str | None,
) -> AnswerResult:
    """Answer, park or reopen clarifications in the workspace. Commits.

    An answer adds no rule and no spec version: a clarification is read with its rule,
    and a prompt gap becomes a task to propose the prompt change. Each answer, park and
    reopen is a decision record. Only a parked question can be reopened.

    Raises:
        ClarificationRefused: A clarification is unknown, already answered or given
            twice, or an answer is not a to d, "park" or "reopen"; every problem is
            listed and nothing is stored.
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
    replacing: dict[uuid.UUID, int] = {}
    forces: dict[uuid.UUID, set[uuid.UUID]] = {}
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
                "a clarification, raise one on the same rule with `replaces_id`."
            )
            continue
        if decision.proposed and decision.answer in (PARK, REOPEN):
            problems.append(
                f"{d}: 'proposed' marks an answer the person confirmed; leave it out "
                f"for '{decision.answer}'."
            )
            continue
        if decision.answer == PARK:
            if c.state is ClarificationState.PARKED:
                problems.append(f"{d}: already parked.")
            continue
        if decision.answer == REOPEN:
            if c.state is not ClarificationState.PARKED:
                problems.append(f"{d}: only a parked question can be reopened.")
            continue
        letters = ANSWER_LETTERS[: len(c.answers)]
        if decision.answer == OTHER:
            text = (decision.text or "").strip()
            if not text:
                problems.append(
                    f"{d}: '{OTHER}' needs the person's answer as text, in their own "
                    "words."
                )
                continue
            if len(text) > MAX_OTHER_LENGTH:
                problems.append(
                    f"{d}: the answer is longer than {MAX_OTHER_LENGTH} characters."
                )
                continue
        elif decision.answer not in letters:
            problems.append(
                f"{d}: answer with one of {', '.join(letters)}, '{OTHER}' with text, "
                f"'{PARK}', or '{REOPEN}' for a parked question."
            )
            continue
        if c.replaces_id:
            if c.agent_id not in forces:
                forces[c.agent_id] = {
                    row.id
                    for rows in clarifications_in_force(
                        session=session, agent_id=c.agent_id
                    ).values()
                    for row in rows
                }
            if c.replaces_id not in forces[c.agent_id]:
                problems.append(
                    f"{d}: the clarification it replaces ({c.replaces_id}) is no "
                    "longer in force; park this question and raise a new one."
                )
            if c.replaces_id in replacing:
                problems.append(
                    f"{d}: answer {replacing[c.replaces_id]} replaces the same "
                    f"clarification {c.replaces_id}."
                )
            replacing[c.replaces_id] = n
    if problems:
        session.rollback()
        raise ClarificationRefused("Nothing was answered", problems)

    by_agent: dict[uuid.UUID, list[Answer]] = defaultdict(list)
    parks: list[Clarification] = []
    reopens: list[Clarification] = []
    for decision in decisions:
        c = found[decision.clarification_id]
        if decision.answer == PARK:
            parks.append(c)
        elif decision.answer == REOPEN:
            reopens.append(c)
        else:
            text = (decision.text or "").strip() if decision.answer == OTHER else None
            by_agent[c.agent_id].append(
                Answer(c, decision.answer, text, decision.proposed)
            )

    for answers in by_agent.values():
        for answer in answers:
            decide(
                session=session,
                clarification=answer.clarification,
                state=ClarificationState.ANSWERED,
                letter=answer.letter,
                decided_by=decided_by,
                assistant_name=assistant_name,
                text=answer.text,
                proposed=answer.proposed,
            )
    for state, rows in (
        (ClarificationState.PARKED, parks),
        (ClarificationState.OPEN, reopens),
    ):
        for c in rows:
            decide(
                session=session,
                clarification=c,
                state=state,
                letter=None,
                decided_by=decided_by,
                assistant_name=assistant_name,
            )
    session.commit()
    return AnswerResult(
        answered=sum(len(a) for a in by_agent.values()),
        parked=len(parks),
        clarifications={
            agent_id: sum(1 for a in answers if not a.clarification.is_gap)
            for agent_id, answers in by_agent.items()
        },
        prompt_gaps={
            agent_id: sum(1 for a in answers if a.clarification.is_gap)
            for agent_id, answers in by_agent.items()
        },
        reopened=len(reopens),
    )


def _name(user: User | None, email: str | None) -> str:
    if user is not None:
        return (user.full_name or "").strip() or user.email.split("@")[0]
    return email.split("@")[0] if email else "someone"


def clarifications_public(
    *, session: Session, rows: Sequence[Clarification]
) -> list[ClarificationPublic]:
    """``rows`` as the assistant reads them, in their order."""
    if not rows:
        return []
    agents = {
        a.id: a
        for a in session.exec(
            select(Agent).where(col(Agent.id).in_({r.agent_id for r in rows}))
        ).all()
    }
    categories = {c.id: c for c in crud.list_categories(session=session)}
    spec_ids = {i for r in rows for i in (r.spec_id, r.answer_spec_id) if i}
    versions = {
        s.id: s.version
        for s in session.exec(select(Spec).where(col(Spec.id).in_(spec_ids))).all()
    }
    user_ids = {i for r in rows for i in (r.raised_by, r.decided_by) if i}
    users = {
        u.id: u
        for u in session.exec(select(User).where(col(User.id).in_(user_ids))).all()
    }
    current_text: dict[tuple[uuid.UUID, str], str] = {}
    for agent_id in {r.agent_id for r in rows if r.rule_key}:
        latest = crud.latest_spec(session=session, agent_id=agent_id)
        if latest is not None:
            for rule in crud.spec_rules(session=session, spec_id=latest.id):
                current_text[(agent_id, rule.key)] = rule.text
    replaced = {
        c.id: chosen_sentence(c)
        for c in session.exec(
            select(Clarification).where(
                col(Clarification.id).in_(
                    {r.replaces_id for r in rows if r.replaces_id}
                )
            )
        ).all()
    }
    out = []
    for r in rows:
        agent = agents.get(r.agent_id)
        category = categories.get(r.category_id)
        out.append(
            ClarificationPublic(
                id=r.id,
                agent_id=r.agent_id,
                agent_name=agent.name if agent else "",
                question=r.question,
                answers=[
                    ClarificationAnswerPublic(
                        letter=letter,
                        label=str(a["label"]),
                        sentence=str(a["sentence"]),
                    )
                    for letter, a in zip(ANSWER_LETTERS, r.answers, strict=False)
                ],
                kind="prompt_gap" if r.is_gap else "clarification",
                rule=ClarifiedRulePublic(
                    key=r.rule_key, text=current_text.get((r.agent_id, r.rule_key))
                )
                if r.rule_key
                else None,
                gap_topic=r.gap_topic,
                replaces_id=r.replaces_id,
                replaces_sentence=replaced.get(r.replaces_id)
                if r.replaces_id
                else None,
                closed=r.closed_at is not None,
                closed_rule_key=r.closed_rule_key,
                category=category.key if category else "",
                category_name=category.name if category else "",
                touches=r.touches,
                calls_seen=len(r.call_ids),
                call_ids=[uuid.UUID(i) for i in r.call_ids],
                spec_version=versions.get(r.spec_id) if r.spec_id else None,
                state=r.state,
                raised_by=_name(
                    users.get(r.raised_by) if r.raised_by else None, r.raised_by_email
                ),
                raised_assistant=r.raised_assistant,
                raised_at=r.raised_at,
                answer=r.answer,
                answer_text=r.answer_text,
                answer_proposed=r.answer_proposed,
                answer_spec_version=versions.get(r.answer_spec_id)
                if r.answer_spec_id
                else None,
                decided_by=_name(
                    users.get(r.decided_by) if r.decided_by else None,
                    r.decided_by_email,
                )
                if r.decided_by_email
                else None,
                decided_assistant=r.decided_assistant,
                decided_at=r.decided_at,
            )
        )
    return out


def counts_public(
    *, session: Session, company_id: uuid.UUID, agent_id: uuid.UUID | None = None
) -> ClarificationCountsPublic:
    counts = state_counts(session=session, company_id=company_id, agent_id=agent_id)
    return ClarificationCountsPublic(
        open=counts[ClarificationState.OPEN],
        answered=counts[ClarificationState.ANSWERED],
        parked=counts[ClarificationState.PARKED],
        answered_this_week=answered_since(
            session=session,
            company_id=company_id,
            agent_id=agent_id,
            since=datetime.now(UTC) - timedelta(days=7),
        ),
    )


def answered_public(
    *, session: Session, company_id: uuid.UUID, result: AnswerResult
) -> ClarificationsAnsweredPublic:
    agents = []
    for agent_id in dict.fromkeys([*result.clarifications, *result.prompt_gaps]):
        agent = session.get(Agent, agent_id)
        agents.append(
            AnsweredAgentPublic(
                agent_id=agent_id,
                agent_name=agent.name if agent else "",
                clarifications=result.clarifications.get(agent_id, 0),
                prompt_gaps=result.prompt_gaps.get(agent_id, 0),
            )
        )
    return ClarificationsAnsweredPublic(
        answered=result.answered,
        parked=result.parked,
        reopened=result.reopened,
        agents=agents,
        open=counts_public(session=session, company_id=company_id).open,
    )
