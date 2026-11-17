"""Storing clarifications and turning answers into spec versions (plan
`plans/2026-11-15-clarifications.md`)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import NamedTuple

from sqlmodel import Session, col, func, select

from app.crud.spec import copy_rule, latest_spec, spec_rules
from app.models.agent import Agent
from app.models.call import Call
from app.models.check import DecisionRecord
from app.models.clarification import ANSWER_LETTERS, OTHER, Clarification
from app.models.enums import (
    ClarificationState,
    DecisionKind,
    SpecOrigin,
    SpecRuleSource,
)
from app.models.spec import Spec, SpecRule
from app.models.user import User


def agent_call_ids(
    *, session: Session, agent_id: uuid.UUID, call_ids: Sequence[uuid.UUID]
) -> set[uuid.UUID]:
    """Those of ``call_ids`` that are the agent's own, not deleted."""
    if not call_ids:
        return set()
    return set(
        session.exec(
            select(Call.id).where(
                col(Call.id).in_(list(call_ids)),
                Call.agent_id == agent_id,
                col(Call.deleted_at).is_(None),
            )
        ).all()
    )


def unanswered(*, session: Session, agent_id: uuid.UUID) -> list[Clarification]:
    """The agent's open and parked clarifications."""
    return list(
        session.exec(
            select(Clarification).where(
                Clarification.agent_id == agent_id,
                Clarification.state != ClarificationState.ANSWERED,
            )
        ).all()
    )


def get_clarifications(
    *,
    session: Session,
    company_id: uuid.UUID,
    ids: Sequence[uuid.UUID],
    lock: bool = False,
) -> dict[uuid.UUID, Clarification]:
    """The workspace's clarifications among ``ids``. With ``lock``, held until commit
    so two decisions on one are made in turn."""
    if not ids:
        return {}
    query = (
        select(Clarification)
        .where(
            col(Clarification.id).in_(list(ids)),
            Clarification.company_id == company_id,
        )
        .order_by(col(Clarification.id))
        .execution_options(populate_existing=True)
    )
    rows = session.exec(query.with_for_update() if lock else query).all()
    return {row.id: row for row in rows}


def open_counts(*, session: Session, company_id: uuid.UUID) -> dict[uuid.UUID, int]:
    """Open clarifications per agent in the workspace, for agents with any."""
    rows = session.exec(
        select(Clarification.agent_id, func.count())
        .where(
            Clarification.company_id == company_id,
            Clarification.state == ClarificationState.OPEN,
        )
        .group_by(col(Clarification.agent_id))
    ).all()
    return dict(rows)


def state_counts(
    *, session: Session, company_id: uuid.UUID, agent_id: uuid.UUID | None = None
) -> dict[ClarificationState, int]:
    """How many clarifications are in each state, in the workspace or for one agent."""
    query = select(Clarification.state, func.count()).where(
        Clarification.company_id == company_id
    )
    if agent_id is not None:
        query = query.where(Clarification.agent_id == agent_id)
    rows = session.exec(query.group_by(col(Clarification.state))).all()
    counts = dict.fromkeys(ClarificationState, 0)
    counts.update(dict(rows))
    return counts


def answered_since(
    *,
    session: Session,
    company_id: uuid.UUID,
    since: datetime,
    agent_id: uuid.UUID | None = None,
) -> int:
    """How many clarifications were answered since ``since``."""
    query = select(func.count()).where(
        Clarification.company_id == company_id,
        Clarification.state == ClarificationState.ANSWERED,
        col(Clarification.decided_at) >= since,
    )
    if agent_id is not None:
        query = query.where(Clarification.agent_id == agent_id)
    return session.exec(query).one()


class Answer(NamedTuple):
    clarification: Clarification
    letter: str
    # For OTHER: the person's own words.
    text: str | None = None


def rule_text(clarification: Clarification, letter: str, text: str | None) -> str:
    """The rule an answer becomes: the chosen answer's rule, or the person's words."""
    if letter == OTHER:
        return text or ""
    return str(clarification.answers[ANSWER_LETTERS.index(letter)]["rule"])


def write_answered_spec(
    *,
    session: Session,
    agent: Agent,
    answers: Sequence[Answer],
    decided_by: User,
    assistant_name: str | None,
) -> Spec:
    """A new spec version: the latest one's rules plus one rule per answer.

    The caller holds the agent lock and has checked the answers. A rule an answer
    replaces is dropped, and the answer's rule takes its key, its critical mark and,
    within the same category, its place. Does not commit.
    """
    previous = latest_spec(session=session, agent_id=agent.id)
    assert previous is not None  # clarifications need a spec
    spec = Spec(
        company_id=agent.company_id,
        agent_id=agent.id,
        version=previous.version + 1,
        agent_version=previous.agent_version,
        prompt_fingerprint=previous.prompt_fingerprint,
        origin=SpecOrigin.ANSWERED,
        written_for=previous.written_for,
        previous_id=previous.id,
        created_by=decided_by.id,
        created_by_email=decided_by.email,
        assistant_name=assistant_name,
    )
    session.add(spec)
    session.flush()
    rules = spec_rules(session=session, spec_id=previous.id)
    old_by_key = {r.key: r for r in rules}
    # A replaced rule the spec has since dropped is not replaced: the answer's rule is
    # new, so a key the assistant dropped never comes back on another rule.
    replaced = {
        a.clarification.replaces_key
        for a in answers
        if a.clarification.replaces_key in old_by_key
    }
    kept = [r for r in rules if r.key not in replaced]
    last: dict[uuid.UUID, int] = {}
    for rule in kept:
        session.add(copy_rule(rule, spec_id=spec.id))
        last[rule.category_id] = max(last.get(rule.category_id, 0), rule.position)
    for answer in answers:
        c = answer.clarification
        old = old_by_key.get(c.replaces_key) if c.replaces_key in replaced else None
        if old is not None and old.category_id == c.category_id:
            position = old.position
        else:
            position = last.get(c.category_id, 0) + 1
            last[c.category_id] = position
        session.add(
            SpecRule(
                company_id=agent.company_id,
                spec_id=spec.id,
                key=old.key if old is not None else uuid.uuid4().hex[:12],
                position=position,
                category_id=c.category_id,
                text=rule_text(c, answer.letter, answer.text),
                source=SpecRuleSource.CLARIFICATION,
                clarification_id=c.id,
                touches=c.touches,
                # It settles the same behaviour as the rule it replaces.
                critical=old.critical if old is not None else False,
            )
        )
    session.flush()
    return spec


def decide(
    *,
    session: Session,
    clarification: Clarification,
    state: ClarificationState,
    letter: str | None,
    answer_spec: Spec | None,
    decided_by: User,
    assistant_name: str | None,
    text: str | None = None,
) -> None:
    """Record an answer, park or reopen on the clarification and as a decision record.
    Does not commit."""
    old = clarification.state
    clarification.state = state
    clarification.answer = letter
    clarification.answer_text = text if letter == OTHER else None
    clarification.answer_spec_id = answer_spec.id if answer_spec else None
    clarification.decided_by = decided_by.id
    clarification.decided_by_email = decided_by.email
    clarification.decided_assistant = assistant_name
    clarification.decided_at = datetime.now(UTC)
    session.add(clarification)
    answered = state is ClarificationState.ANSWERED
    kind = {
        ClarificationState.ANSWERED: DecisionKind.CLARIFICATION_ANSWERED,
        ClarificationState.PARKED: DecisionKind.CLARIFICATION_PARKED,
        ClarificationState.OPEN: DecisionKind.CLARIFICATION_REOPENED,
    }[state]
    detail = None
    if answered and letter is not None and answer_spec is not None:
        detail = {
            "rule": rule_text(clarification, letter, text),
            "spec_version": answer_spec.version,
        }
    session.add(
        DecisionRecord(
            company_id=clarification.company_id,
            agent_id=clarification.agent_id,
            kind=kind,
            subject=str(clarification.id),
            old_value=old.value,
            new_value=letter if answered else state.value,
            decided_by=decided_by.id,
            decided_by_email=decided_by.email,
            assistant_name=assistant_name,
            detail=detail,
        )
    )


def list_page(
    *,
    session: Session,
    company_id: uuid.UUID,
    state: ClarificationState,
    agent_id: uuid.UUID | None,
    offset: int,
    limit: int,
) -> tuple[list[Clarification], bool]:
    """A page of the workspace's clarifications in ``state`` and whether more follow:
    open ones most important first, answered and parked ones newest first."""
    query = select(Clarification).where(
        Clarification.company_id == company_id, Clarification.state == state
    )
    if agent_id is not None:
        query = query.where(Clarification.agent_id == agent_id)
    if state is ClarificationState.OPEN:
        # Most important first: seen on more calls, then touching money, safety or
        # compliance, then the newest. No criticality yet.
        order = (
            func.jsonb_array_length(col(Clarification.call_ids)).desc(),
            col(Clarification.touches).is_(None),
            col(Clarification.raised_at).desc(),
            col(Clarification.id),
        )
    else:
        order = (
            func.coalesce(
                col(Clarification.decided_at), col(Clarification.raised_at)
            ).desc(),
            col(Clarification.id),
        )
    rows = list(
        session.exec(query.order_by(*order).offset(offset).limit(limit + 1)).all()
    )
    return rows[:limit], len(rows) > limit
