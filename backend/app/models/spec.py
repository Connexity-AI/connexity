"""Each agent's spec: what it is supposed to do, as plain rules, version by version.

The assistant writes it from the agent's prompt, guided by `connexity://guides/spec`;
Connexity stores it. A new agent version adopts the previous spec. Rules are never
edited: any change is a new spec version, so every version stays as it was written.
See `plans/2026-11-14-spec.md`.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint, text
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import SpecOrigin, SpecRuleSource, SpecRuleTouches


def _now() -> datetime:
    return datetime.now(UTC)


class Spec(SQLModel, table=True):
    """One version of an agent's spec. The highest ``version`` is the agent's spec."""

    __tablename__ = "spec"
    __table_args__ = (
        UniqueConstraint("agent_id", "version", name="uq_spec_agent_version"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("agent.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    # 1, 2, 3 … per agent.
    version: int
    # The agent version it was written for, as calls record it ("14").
    agent_version: str = Field(max_length=255)
    # The fingerprint of that version's prompt or flow in the catalogue, when known.
    prompt_fingerprint: str | None = Field(default=None, max_length=64)
    origin: SpecOrigin = Field(sa_type=enum_type(SpecOrigin))
    # The spec version this one follows; none for the first.
    previous_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("spec.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    # Who wrote it, as on decision records. None for a copy Connexity adopted.
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    created_by_email: str | None = Field(default=None, max_length=255)
    # The assistant that wrote it with the person's approval ("Claude Code").
    assistant_name: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class SpecRule(SQLModel, table=True):
    """One rule of one spec version, in one plain sentence."""

    __tablename__ = "spec_rule"
    __table_args__ = (UniqueConstraint("spec_id", "key", name="uq_spec_rule_key"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    spec_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("spec.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    # The same rule across versions carries the same key, so versions can be compared:
    # kept, added, dropped.
    key: str = Field(max_length=64)
    # Its order within its category.
    position: int
    # One of the fixed categories (`app/models/category.py`). A category in use cannot
    # be deleted.
    category_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("category.id", ondelete="RESTRICT"), nullable=False, index=True
        )
    )
    text: str = Field(sa_column=Column("text", Text, nullable=False))
    source: SpecRuleSource = Field(sa_type=enum_type(SpecRuleSource))
    # For a rule from the prompt: the prompt's words it rests on.
    quote: str | None = Field(default=None, sa_column=Column("quote", Text))
    # For a rule from a clarification. A plain id until clarifications (10.12) add
    # their table and its foreign key.
    clarification_id: uuid.UUID | None = Field(default=None)
    touches: SpecRuleTouches | None = Field(
        default=None, sa_type=enum_type(SpecRuleTouches)
    )
