"""Clarifications: questions about an agent's behaviour that its spec does not settle.

Each has two to four fixed answers, and each answer carries the rule it becomes. An
answer adds that rule to the agent's spec in a new spec version. See
`plans/2026-11-15-clarifications.md`.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import ClarificationState, SpecRuleTouches


def _now() -> datetime:
    return datetime.now(UTC)


# The answers' letters, in order.
ANSWER_LETTERS = ("a", "b", "c", "d")


class Clarification(SQLModel, table=True):
    """One question on one agent: open, answered or parked."""

    __tablename__ = "clarification"
    __table_args__ = (
        Index("ix_clarification_agent_state", "agent_id", "state"),
        # One open or parked question per wording on an agent; an answered one may be
        # asked again (it replaces its rule).
        Index(
            "ix_clarification_one_unanswered_question",
            "agent_id",
            "question_key",
            unique=True,
            postgresql_where=text("state <> 'answered'"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("agent.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    # The spec version it was raised against.
    spec_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("spec.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    question: str = Field(sa_column=Column("question", Text, nullable=False))
    # The question normalised (lower case, no punctuation), to catch the same question
    # asked twice.
    question_key: str = Field(sa_column=Column("question_key", Text, nullable=False))
    # Two to four, in order a to d: [{"label": ..., "rule": ...}].
    answers: list[dict[str, Any]] = Field(
        sa_column=Column("answers", JSONB, nullable=False)
    )
    # The category and marker the answer's rule takes.
    category_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("category.id", ondelete="RESTRICT"), nullable=False, index=True
        )
    )
    touches: SpecRuleTouches | None = Field(
        default=None, sa_type=enum_type(SpecRuleTouches)
    )
    # The calls where the behaviour was seen, as ids; empty for a question raised from
    # a prompt change. Not foreign keys, so a deleted call does not delete the question.
    call_ids: list[str] = Field(
        default_factory=list, sa_column=Column("call_ids", JSONB, nullable=False)
    )
    # The key of the spec rule the answer replaces, if any.
    replaces_key: str | None = Field(default=None, max_length=64)
    state: ClarificationState = Field(
        default=ClarificationState.OPEN, sa_type=enum_type(ClarificationState)
    )
    # The chosen answer's letter, once answered.
    answer: str | None = Field(default=None, max_length=1)
    # The spec version the answer made.
    answer_spec_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("spec.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    # Who raised it. None, with "Connexity" as the email, once Connexity raises them.
    raised_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    raised_by_email: str = Field(max_length=255)
    raised_assistant: str | None = Field(default=None, max_length=255)
    raised_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )
    # The latest answer or park: who decided (the person, with the assistant that
    # acted for them) and when. Earlier parks are in the decision records.
    decided_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    decided_by_email: str | None = Field(default=None, max_length=255)
    decided_assistant: str | None = Field(default=None, max_length=255)
    decided_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )


class ClarificationAnswerPublic(BaseModel):
    letter: str = Field(description="a to d; pass it to `answer_clarifications`")
    label: str
    rule: str = Field(description="The spec rule this answer becomes")


class ReplacedRulePublic(BaseModel):
    key: str
    text: str | None = Field(
        default=None,
        description="The rule's text in the agent's latest spec; None if dropped since",
    )


class ClarificationPublic(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    question: str
    answers: list[ClarificationAnswerPublic]
    category: str = Field(description="The category key the rule takes")
    category_name: str
    touches: SpecRuleTouches | None = None
    calls_seen: int = Field(description="How many calls were given as evidence")
    call_ids: list[uuid.UUID]
    spec_version: int | None = Field(
        default=None, description="The spec version it was raised against"
    )
    replaces: ReplacedRulePublic | None = Field(
        default=None, description="The spec rule the answer replaces"
    )
    state: ClarificationState
    raised_by: str
    raised_assistant: str | None = None
    raised_at: datetime
    answer: str | None = Field(default=None, description="The chosen letter")
    answer_spec_version: int | None = Field(
        default=None, description="The spec version the answer made"
    )
    decided_by: str | None = Field(
        default=None, description="The person who answered or parked it"
    )
    decided_assistant: str | None = Field(
        default=None, description="The assistant that acted for them"
    )
    decided_at: datetime | None = None


class ClarificationCountsPublic(BaseModel):
    open: int
    answered: int
    parked: int


class ClarificationListPublic(BaseModel):
    counts: ClarificationCountsPublic = Field(
        description="For the same agent filter, every state"
    )
    data: list[ClarificationPublic]


class AnsweredSpecPublic(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    spec_version: int = Field(description="The new spec version the answers made")
    rules_added: int


class ClarificationsAnsweredPublic(BaseModel):
    answered: int
    parked: int
    specs: list[AnsweredSpecPublic]
    open: int = Field(description="Open clarifications left in the workspace")
