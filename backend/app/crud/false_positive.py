"""Findings marked as false positives, and spec flags the LLM step dismissed (roadmap
105.17, plan `plans/2026-11-27-false-positives.md`).

A marked finding stays stored with who marked it, when, why, the clarification it rests
on and who approved it. A dismissed flag is not a finding: it is a verdict in the spec
check's stored answer (``ModelAnswer``), read here by the issue's rule key.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, Text, and_, column, or_, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Session, col, func, select

from app.models.call import Call, CallEvent
from app.models.check import Finding, Issue
from app.models.enums import FindingEffect, ModelAnswerStatus, SpecCheckType
from app.models.model_answer import ModelAnswer

SPEC_CHECK_TYPE = "spec_rule_broken"
# The LLM step's verdicts that dismiss a flag.
_DISMISSED = ("passed", "did_not_come_up")


def issue_findings(
    *, session: Session, issue_id: uuid.UUID, ids: Sequence[uuid.UUID]
) -> list[Finding]:
    """The issue's findings among ``ids``, marked or not."""
    if not ids:
        return []
    return list(
        session.exec(
            select(Finding).where(
                Finding.issue_id == issue_id, col(Finding.id).in_(list(ids))
            )
        ).all()
    )


def _marked(issue_id: uuid.UUID) -> ColumnElement[bool]:
    return and_(
        col(Finding.issue_id) == issue_id, col(Finding.false_positive_at).is_not(None)
    )


def marked_count(*, session: Session, issue_id: uuid.UUID) -> int:
    return int(
        session.exec(
            select(func.count()).select_from(Finding).where(_marked(issue_id))
        ).one()
    )


def marked_rows(
    *, session: Session, issue_id: uuid.UUID, offset: int, limit: int
) -> list[tuple[Finding, Call]]:
    """The issue's marked findings with their calls, newest marking first."""
    return list(
        session.exec(
            select(Finding, Call)
            .join(Call, col(Call.id) == col(Finding.call_id))
            .where(_marked(issue_id), col(Call.deleted_at).is_(None))
            .order_by(col(Finding.false_positive_at).desc(), col(Finding.id).desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )


def marked_count_for_check(
    *, session: Session, agent_id: uuid.UUID, check_type: str
) -> int:
    """The agent's findings of one check marked as false positives. A number only:
    nothing is suppressed because of it."""
    return int(
        session.exec(
            select(func.count())
            .select_from(Finding)
            .where(
                Finding.agent_id == agent_id,
                Finding.check_type == check_type,
                col(Finding.false_positive_at).is_not(None),
            )
        ).one()
    )


def _dismissed(agent_id: uuid.UUID, key: str | None) -> list[ColumnElement[bool]]:
    """Stored spec answers of the agent's calls where the LLM step dismissed the flag
    on ``key`` (any rule when None), not brought back."""
    conditions: list[ColumnElement[bool]] = [
        col(ModelAnswer.check_type) == SPEC_CHECK_TYPE,
        col(ModelAnswer.status) == ModelAnswerStatus.OK,
        col(Call.agent_id) == agent_id,
        col(Call.deleted_at).is_(None),
    ]
    if key is None:
        return conditions
    rule = col(ModelAnswer.answer)["rules"][key]
    return [
        *conditions,
        rule["check"].astext == SpecCheckType.CLASSIFIER_THEN_LLM.value,
        rule["verdict"]["outcome"].astext.in_(_DISMISSED),
        rule["verdict"]["brought_back"].is_(None),
    ]


def dismissed_count(*, session: Session, issue: Issue) -> int:
    if issue.check_type != SPEC_CHECK_TYPE or not issue.key:
        return 0
    return int(
        session.exec(
            select(func.count())
            .select_from(ModelAnswer)
            .join(Call, col(Call.id) == col(ModelAnswer.call_id))
            .where(*_dismissed(issue.agent_id, issue.key))
        ).one()
    )


def dismissed_rows(
    *, session: Session, issue: Issue, offset: int, limit: int
) -> list[tuple[ModelAnswer, Call]]:
    """The answers holding the issue's rule's dismissed flags, newest call first."""
    if issue.check_type != SPEC_CHECK_TYPE or not issue.key:
        return []
    return list(
        session.exec(
            select(ModelAnswer, Call)
            .join(Call, col(Call.id) == col(ModelAnswer.call_id))
            .where(*_dismissed(issue.agent_id, issue.key))
            .order_by(col(Call.started_at).desc(), col(Call.id).desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )


def dismissed_answers_on(
    *, session: Session, issue: Issue, call_ids: Sequence[uuid.UUID]
) -> list[tuple[ModelAnswer, Call]]:
    """The answers on these calls that hold a dismissed flag on the issue's rule."""
    if issue.check_type != SPEC_CHECK_TYPE or not issue.key or not call_ids:
        return []
    return list(
        session.exec(
            select(ModelAnswer, Call)
            .join(Call, col(Call.id) == col(ModelAnswer.call_id))
            .where(
                *_dismissed(issue.agent_id, issue.key),
                col(Call.id).in_(list(call_ids)),
            )
        ).all()
    )


def dismissed_count_for_agent(*, session: Session, agent_id: uuid.UUID) -> int:
    """Flags the LLM step dismissed on the agent's calls, over every rule, counted in
    the database: one row per rule of each stored answer."""
    rules = (
        func.jsonb_each(col(ModelAnswer.answer)["rules"])
        .table_valued(column("key", Text), column("value", JSONB))
        .render_derived(name="rule_answer")
    )
    return int(
        session.exec(
            select(func.count())
            .select_from(ModelAnswer)
            .join(Call, col(Call.id) == col(ModelAnswer.call_id))
            .join(rules, true())
            .where(
                *_dismissed(agent_id, None),
                rules.c.value["check"].astext
                == SpecCheckType.CLASSIFIER_THEN_LLM.value,
                rules.c.value["verdict"]["outcome"].astext.in_(_DISMISSED),
                rules.c.value["verdict"]["brought_back"].is_(None),
            )
        ).one()
    )


def any_finding_fails(*, session: Session, issue_id: uuid.UUID) -> bool:
    """Whether any of the issue's findings fails its call, marked ones included: an
    issue whose findings are all marked keeps its severity."""
    return bool(
        session.exec(
            select(func.bool_or(col(Finding.effect) == FindingEffect.FAILS)).where(
                Finding.issue_id == issue_id
            )
        ).one()
    )


def event_starts(
    *, session: Session, wanted: Sequence[tuple[uuid.UUID, Sequence[str]]]
) -> dict[tuple[uuid.UUID, str], int]:
    """When each of these calls' events started, in milliseconds."""
    pairs = [(call_id, key) for call_id, keys in wanted for key in keys]
    if not pairs:
        return {}
    match = or_(
        *(
            and_(col(CallEvent.call_id) == call_id, col(CallEvent.key) == key)
            for call_id, key in pairs
        )
    )
    return {
        (call_id, key): start or 0
        for call_id, key, start in session.exec(
            select(CallEvent.call_id, CallEvent.key, CallEvent.start_ms).where(match)
        ).all()
    }
