"""Questions for the person about an agent's behaviour, of two kinds (plan
`plans/2026-11-26-clarification-on-rule.md`):

- A **clarification** explains an existing spec rule (``rule_key``): its answer is one
  sentence attached to that rule, read with it by every check. The rule itself changes
  only when the prompt does.
- A **prompt gap** is behaviour no rule covers (no ``rule_key``): its answer is the
  person's decision about what the prompt should say. The assistant proposes the prompt
  change; a spec written from the new prompt closes the gap (``closed_rule_key``).

Each has two to four fixed answers, each with the sentence it adds.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, Index, Text, false, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import ClarificationState, SpecRuleTouches


def _now() -> datetime:
    return datetime.now(UTC)


# The answers' letters, in order.
ANSWER_LETTERS = ("a", "b", "c", "d")
# "Something else": the person writes the rule themselves (answer_text).
OTHER = "other"


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
    # Two to four, in order a to d: [{"label": ..., "sentence": ...}]. The sentence is
    # the clarification the answer adds, or for a prompt gap what the prompt would say.
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
    # The spec rule it explains; none for a prompt gap.
    rule_key: str | None = Field(default=None, max_length=64, index=True)
    # For a prompt gap: a few words naming the behaviour ("changing appointments").
    gap_topic: str | None = Field(default=None, max_length=100)
    # The earlier clarification on the same rule this one's answer replaces.
    replaces_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("clarification.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    state: ClarificationState = Field(
        default=ClarificationState.OPEN, sa_type=enum_type(ClarificationState)
    )
    # The chosen answer's letter, once answered.
    answer: str | None = Field(default=None, max_length=8)
    # For the answer "other": the person's own words, which became the rule.
    answer_text: str | None = Field(
        default=None, sa_column=Column("answer_text", Text, nullable=True)
    )
    # The assistant proposed the answer and the person confirmed it.
    answer_proposed: bool = Field(
        default=False, sa_column_kwargs={"server_default": false()}
    )
    # For an answer before 2026-11-26 (roadmap 105.12): the spec version it made, with
    # its answer as a rule. Answers no longer make spec versions.
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
    # For an answered prompt gap: the spec version written from a prompt that covers
    # it, and the rule that does.
    closed_spec_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("spec.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    closed_rule_key: str | None = Field(default=None, max_length=64)
    closed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )

    @property
    def is_gap(self) -> bool:
        return self.rule_key is None


class ClarificationAnswerPublic(BaseModel):
    letter: str = Field(description="a to d; pass it to `answer_clarifications`")
    label: str
    sentence: str = Field(
        description="The clarification this answer adds to the rule; for a prompt gap, "
        "what the prompt would need to say"
    )


class ClarifiedRulePublic(BaseModel):
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
    kind: Literal["clarification", "prompt_gap"] = Field(
        description="clarification: it explains `rule`; prompt_gap: behaviour no rule "
        "covers, which the prompt should settle"
    )
    rule: ClarifiedRulePublic | None = Field(
        default=None, description="For a clarification: the rule it explains"
    )
    gap_topic: str | None = Field(
        default=None, description="For a prompt gap: the behaviour, in a few words"
    )
    replaces_id: uuid.UUID | None = Field(
        default=None,
        description="The earlier clarification on the same rule its answer replaces",
    )
    replaces_sentence: str | None = Field(
        default=None, description="That earlier clarification, as answered"
    )
    closed: bool = Field(
        default=False,
        description="For an answered prompt gap: a spec written from a prompt that "
        "covers it closed it",
    )
    closed_rule_key: str | None = Field(
        default=None, description="For a closed prompt gap: the rule that covers it"
    )
    state: ClarificationState
    raised_by: str
    raised_assistant: str | None = None
    raised_at: datetime
    answer: str | None = Field(
        default=None, description="The chosen letter, or 'other' with answer_text"
    )
    answer_text: str | None = Field(
        default=None,
        description="For 'other': the person's own words, kept as the sentence",
    )
    answer_proposed: bool = Field(
        default=False,
        description="The assistant proposed the answer and the person confirmed it",
    )
    answer_spec_version: int | None = Field(
        default=None,
        description="Only for an answer from before answers stopped making spec "
        "versions (2026-11-26): the version it made",
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
    answered_this_week: int = Field(
        default=0, description="Answered in the last 7 days"
    )


class ClarificationListPublic(BaseModel):
    counts: ClarificationCountsPublic = Field(
        description="For the same agent filter, every state"
    )
    data: list[ClarificationPublic]


class AnsweredAgentPublic(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    clarifications: int = Field(description="Clarifications added to its rules")
    prompt_gaps: int = Field(
        description="Prompt gaps answered: each is now a task to propose the prompt "
        "change"
    )


class ClarificationsAnsweredPublic(BaseModel):
    answered: int
    parked: int
    reopened: int = 0
    agents: list[AnsweredAgentPublic]
    open: int = Field(description="Open questions left in the workspace")
