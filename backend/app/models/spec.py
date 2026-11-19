"""Each agent's spec: what it is supposed to do, as plain rules, version by version.

The assistant writes it from the agent's prompt, guided by `connexity://guides/spec`;
Connexity stores it. A new agent version adopts the previous spec. Rules are never
edited: any change is a new spec version, so every version stays as it was written.
See `plans/2026-11-14-spec.md`.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint, false, text
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
    # The agent version its prompt rules were last written for. A written version sets
    # it; an adopted or answered one keeps its predecessor's, so answering questions
    # never stands in for reviewing a new prompt. None until a version is written.
    written_for: str | None = Field(default=None, max_length=255)
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
    # For a rule from a clarification: the clarification whose answer it is.
    clarification_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("clarification.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    touches: SpecRuleTouches | None = Field(
        default=None, sa_type=enum_type(SpecRuleTouches)
    )
    # A failed critical rule fails the version in testing; any other is a Warning
    # (`docs-internal/testing.md`, decision 6). Carried by key into later versions.
    critical: bool = Field(default=False, sa_column_kwargs={"server_default": false()})


SpecState = Literal["none", "current", "needs_review"]


class SpecRulePublic(BaseModel):
    key: str = Field(
        description="The same across versions; pass it back to keep a rule"
    )
    text: str
    source: SpecRuleSource
    quote: str | None = Field(
        default=None, description="The prompt's words it rests on"
    )
    touches: SpecRuleTouches | None = None
    critical: bool = Field(
        default=False, description="A failure of this rule must stop a release"
    )
    scenarios: int = Field(
        default=0,
        description="How many active scenarios list it; coverage counts the rules with "
        "at least one",
    )
    answered_by: str | None = Field(
        default=None, description="For a rule from a clarification: who answered it"
    )
    answered_at: datetime | None = None
    in_conflict: bool = Field(
        default=False,
        description="An open or parked clarification replaces this rule",
    )
    result: (
        Literal["passed", "failed", "flaky", "did_not_come_up", "no_scenario"] | None
    ) = Field(
        default=None,
        description="Its result in the live version's latest full run; none without one",
    )
    change: Literal["kept", "added", "dropped"] | None = Field(
        default=None,
        description="With compare: kept, added, or dropped (only in the earlier version)",
    )


class SpecGroupPublic(BaseModel):
    category: str = Field(description="The category's key")
    name: str
    rules: list[SpecRulePublic]


class SpecVersionPublic(BaseModel):
    version: int
    agent_version: str = Field(description="The agent version it was written for")
    origin: SpecOrigin
    written_by: str | None = Field(
        default=None, description="The person; None for a copy Connexity adopted"
    )
    assistant: str | None = None
    created_at: datetime
    rule_count: int


class SpecCountsPublic(BaseModel):
    from_prompt: int
    from_clarifications: int
    in_conflict: int
    critical: int = Field(default=0, description="Rules marked critical")


class SpecComparisonPublic(BaseModel):
    version: int = Field(description="The earlier version compared with")
    kept: int
    added: int
    dropped: int


class SpecPublic(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    current_agent_version: str | None = Field(
        default=None, description="The agent version of its most recent call"
    )
    state: SpecState
    spec: SpecVersionPublic | None = Field(
        default=None, description="None while the agent has no spec"
    )
    latest_version: int | None = Field(
        default=None, description="The agent's newest spec version"
    )
    groups: list[SpecGroupPublic] = Field(
        default_factory=list, description="In the fixed categories' order"
    )
    open_clarifications: int = Field(
        default=0, description="Questions about this agent waiting for the person"
    )
    counts: SpecCountsPublic | None = Field(
        default=None, description="The shown version's rules by source, and conflicts"
    )
    versions: list[SpecVersionPublic] = Field(
        default_factory=list,
        description="Every version of the agent's spec, newest first",
    )
    results_version: str | None = Field(
        default=None, description="The live version, whose full run gave `result`"
    )
    results_at: datetime | None = Field(
        default=None, description="When that full run completed; none without one"
    )
    comparison: SpecComparisonPublic | None = Field(
        default=None, description="With compare: how the shown version differs"
    )


class SpecChangesPublic(BaseModel):
    rules: int
    kept: int
    added: int
    dropped: int
    carried: int = Field(
        description="Rules from answered clarifications, carried over unchanged"
    )
    quotes_checked: bool = Field(
        description="False when Connexity has no prompt for the version to check against"
    )


class SpecWrittenPublic(SpecPublic):
    changes: SpecChangesPublic
