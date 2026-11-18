"""The queries behind the assistant's task list (`app/services/work.py`)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy import and_, exists
from sqlmodel import Session, col, func, select

from app.crud.check import shown_finding
from app.models.agent import Agent
from app.models.assistant_task import AssistantTask
from app.models.call import Call
from app.models.check import CallCheck, DecisionRecord, Finding
from app.models.clarification import Clarification
from app.models.enums import (
    AssistantTaskState,
    CheckOutcome,
    ClarificationState,
    DecisionKind,
    IssueState,
    SpecOrigin,
    TaskKind,
)
from app.models.spec import Spec

OPEN_STATES = (AssistantTaskState.IN_PROGRESS,)


class OpenQuestions(NamedTuple):
    questions: int
    calls: int  # distinct calls the questions were seen on
    oldest: datetime


def open_questions_by_agent(
    *, session: Session, company_id: uuid.UUID
) -> dict[uuid.UUID, OpenQuestions]:
    """Each agent's open clarifications: how many, on how many distinct calls, and
    when the oldest was raised."""
    rows = session.exec(
        select(
            Clarification.agent_id, Clarification.call_ids, Clarification.raised_at
        ).where(
            Clarification.company_id == company_id,
            Clarification.state == ClarificationState.OPEN,
        )
    ).all()
    calls: dict[uuid.UUID, set[str]] = {}
    count: dict[uuid.UUID, int] = {}
    oldest: dict[uuid.UUID, datetime] = {}
    for agent_id, call_ids, raised_at in rows:
        calls.setdefault(agent_id, set()).update(call_ids or [])
        count[agent_id] = count.get(agent_id, 0) + 1
        if agent_id not in oldest or raised_at < oldest[agent_id]:
            oldest[agent_id] = raised_at
    return {
        agent_id: OpenQuestions(count[agent_id], len(calls[agent_id]), oldest[agent_id])
        for agent_id in count
    }


def unchecked_calls_by_agent(
    *,
    session: Session,
    company_id: uuid.UUID,
    since: dict[uuid.UUID, datetime],
    default_since: datetime,
) -> dict[uuid.UUID, int]:
    """Each linked agent's calls that started after its ``since`` (or
    ``default_since``) that no check could run on and that have no finding: the Calls
    page's "unchecked"."""
    shown = exists().where(and_(Finding.call_id == Call.id, shown_finding()))
    ran = exists().where(
        CallCheck.call_id == Call.id, CallCheck.outcome == CheckOutcome.RAN
    )
    rows = session.exec(
        select(Call.agent_id, Call.started_at)
        .join(Agent, col(Agent.id) == col(Call.agent_id))
        .where(
            Call.company_id == company_id,
            col(Agent.integration_id).is_not(None),
            col(Call.deleted_at).is_(None),
            col(Call.started_at) >= _naive(default_since),
            ~shown,
            ~ran,
        )
    ).all()
    out: dict[uuid.UUID, int] = {}
    for agent_id, started_at in rows:
        if agent_id is None:
            continue
        after = since.get(agent_id)
        if after is not None and started_at is not None and started_at < _naive(after):
            continue
        out[agent_id] = out.get(agent_id, 0) + 1
    return out


def last_reviews(
    *, session: Session, company_id: uuid.UUID
) -> dict[uuid.UUID, datetime]:
    """When each agent's calls were last handed out for review."""
    rows = session.exec(
        select(AssistantTask.agent_id, func.max(AssistantTask.taken_at))
        .where(
            AssistantTask.company_id == company_id,
            AssistantTask.kind == TaskKind.CALLS_TO_REVIEW,
            col(AssistantTask.agent_id).is_not(None),
        )
        .group_by(col(AssistantTask.agent_id))
    ).all()
    return {agent_id: taken_at for agent_id, taken_at in rows if agent_id is not None}


def open_tasks(*, session: Session, company_id: uuid.UUID) -> list[AssistantTask]:
    """Tasks an assistant holds or that wait for the person, oldest first."""
    return list(
        session.exec(
            select(AssistantTask)
            .where(
                AssistantTask.company_id == company_id,
                col(AssistantTask.state).in_(OPEN_STATES),
            )
            .order_by(col(AssistantTask.taken_at))
        ).all()
    )


def end_tasks(
    *,
    session: Session,
    rows: Sequence[AssistantTask],
    state: AssistantTaskState,
) -> None:
    """Move rows to ``state``, stamping when. Does not commit."""
    now = datetime.now(UTC)
    for row in rows:
        if row.ended_at is None:
            row.ended_at = now
        if state is AssistantTaskState.DONE:
            row.done_at = now
        row.state = state
        session.add(row)


def _naive(moment: datetime) -> datetime:
    """Call times are stored naive, in UTC."""
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(UTC).replace(tzinfo=None)


def done_tasks(
    *,
    session: Session,
    company_id: uuid.UUID,
    since: datetime,
    kinds: Sequence[TaskKind],
) -> list[AssistantTask]:
    """Tasks of ``kinds`` that assistants finished since ``since``."""
    return list(
        session.exec(
            select(AssistantTask).where(
                AssistantTask.company_id == company_id,
                AssistantTask.state == AssistantTaskState.DONE,
                col(AssistantTask.kind).in_(kinds),
                col(AssistantTask.done_at) >= since,
            )
        ).all()
    )


def specs_since(
    *, session: Session, company_id: uuid.UUID, since: datetime
) -> list[Spec]:
    """Spec versions written or made by answers since ``since``."""
    return list(
        session.exec(
            select(Spec).where(
                Spec.company_id == company_id,
                col(Spec.origin).in_((SpecOrigin.WRITTEN, SpecOrigin.ANSWERED)),
                col(Spec.created_at) >= since,
            )
        ).all()
    )


def answers_by_spec(
    *, session: Session, spec_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many answers made each spec version."""
    if not spec_ids:
        return {}
    rows = session.exec(
        select(Clarification.answer_spec_id, func.count())
        .where(col(Clarification.answer_spec_id).in_(spec_ids))
        .group_by(col(Clarification.answer_spec_id))
    ).all()
    return {spec_id: n for spec_id, n in rows if spec_id is not None}


def issue_decisions_since(
    *, session: Session, company_id: uuid.UUID, since: datetime
) -> list[DecisionRecord]:
    """Issues resolved or archived since ``since``."""
    return list(
        session.exec(
            select(DecisionRecord).where(
                DecisionRecord.company_id == company_id,
                DecisionRecord.kind == DecisionKind.ISSUE_STATE,
                col(DecisionRecord.new_value).in_(
                    (IssueState.RESOLVED.value, IssueState.ARCHIVED.value)
                ),
                col(DecisionRecord.created_at) >= since,
            )
        ).all()
    )
