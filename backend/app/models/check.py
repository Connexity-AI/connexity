"""Findings, the decisions that govern checks, and when each check first existed.

The model is the vision's section 7. A check itself is code (``app.services.checks``),
not a row.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import AwareDatetime, JsonValue
from sqlalchemy import Column, DateTime, ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import (
    CheckKind,
    CheckMode,
    CheckOutcome,
    DecisionKind,
    FindingEffect,
    IssueState,
)

CHECK_TYPE_MAX_LENGTH = 64


def _now() -> datetime:
    return datetime.now(UTC)


class Finding(SQLModel, table=True):
    """One thing wrong at one moment in one call, raised by one version of one check."""

    __tablename__ = "finding"
    __table_args__ = (
        # An agent's findings of one type and key: what an issue is made of.
        Index("ix_finding_agent_type_key", "agent_id", "check_type", "key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("agent.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    call_id: uuid.UUID = Field(foreign_key="call.id", index=True, ondelete="CASCADE")
    issue_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("issue.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    check_type: str = Field(max_length=CHECK_TYPE_MAX_LENGTH)
    check_version: int
    kind: CheckKind = Field(sa_type=enum_type(CheckKind))
    # The one thing that says what broke, as the check's type defines it (a tool's
    # name). Null for a type with no key.
    key: str | None = Field(default=None, max_length=255)
    # The events' ids in the trace, not their rows: replacing a trace rewrites the rows.
    event_keys: list[str] = Field(sa_column=Column("event_keys", JSONB, nullable=False))
    detail: dict[str, Any] | None = Field(
        default=None, sa_column=Column("detail", JSONB(none_as_null=True))
    )
    # The check's setting when the call started. Never changed afterwards.
    effect: FindingEffect = Field(sa_type=enum_type(FindingEffect))
    # The call started before this check existed: shown, counted for nothing.
    retroactive: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class Issue(SQLModel, table=True):
    """All findings with the same symptom on one agent. It lives forever.

    Its identity is the agent, the check's type and the key that type defines. When it
    was first and last seen, and how much it holds, are read from its findings.
    """

    __tablename__ = "issue"
    __table_args__ = (
        UniqueConstraint("agent_id", "check_type", "key", name="uq_issue_identity"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("agent.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    check_type: str = Field(max_length=CHECK_TYPE_MAX_LENGTH)
    # Empty for a type with no key, so that the identity is still unique.
    key: str = Field(default="", max_length=255)
    state: IssueState = Field(
        default=IssueState.OPEN, sa_type=enum_type(IssueState), index=True
    )
    # The last time a person resolved it. Kept when it regresses.
    resolved_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    # The version said to carry the fix, as the person wrote it. A note, not a rule.
    resolved_version: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class CallCheck(SQLModel, table=True):
    """What one check did on one call, the last time the call was checked."""

    __tablename__ = "call_check"

    call_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("call.id", ondelete="CASCADE"), primary_key=True, nullable=False
        )
    )
    check_type: str = Field(max_length=CHECK_TYPE_MAX_LENGTH, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    check_version: int
    outcome: CheckOutcome = Field(sa_type=enum_type(CheckOutcome))
    # For a skipped check: what the call's trace lacks.
    missing: str | None = Field(default=None, max_length=255)
    ran_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class DecisionRecord(SQLModel, table=True):
    """Who decided what, when and why. Append only."""

    __tablename__ = "decision_record"
    __table_args__ = (
        Index("ix_decision_record_agent_kind_subject", "agent_id", "kind", "subject"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("agent.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    kind: DecisionKind = Field(sa_type=enum_type(DecisionKind))
    # What the decision applied to. For a check setting, the check's type.
    subject: str = Field(max_length=255)
    old_value: str | None = Field(default=None, max_length=255)
    new_value: str | None = Field(default=None, max_length=255)
    reason: str | None = Field(default=None, sa_column=Column("reason", Text))
    decided_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    # Kept beside the id so the record still says who after the user is removed.
    decided_by_email: str = Field(max_length=255)
    created_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
        index=True,
    )


class CheckRelease(SQLModel, table=True):
    """When a version of a built-in check was first present in this installation.

    Not owned by a company: the library of checks is the same for everyone.
    """

    __tablename__ = "check_release"

    check_type: str = Field(max_length=CHECK_TYPE_MAX_LENGTH, primary_key=True)
    version: int = Field(primary_key=True)
    first_seen_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class FindingPublic(SQLModel):
    id: uuid.UUID
    issue_id: uuid.UUID
    check_type: str
    check_version: int
    kind: CheckKind
    title: str = Field(description="The check's name; empty for a check since removed")
    key: str | None = None
    event_ids: list[str] = Field(description="Ids of the trace events it points at")
    detail: dict[str, JsonValue] | None = None
    effect: FindingEffect
    retroactive: bool = Field(
        description="True when the call started before this check existed"
    )
    created_at: AwareDatetime


class AgentCheckPublic(SQLModel):
    type: str
    title: str
    description: str
    kind: CheckKind
    version: int
    default_mode: CheckMode
    mode: CheckMode = Field(description="What the check does for this agent now")


class CheckModeUpdate(SQLModel):
    mode: CheckMode
    reason: str | None = Field(
        default=None,
        max_length=2000,
        description="Required when the change loosens the check",
    )


class DecisionRecordPublic(SQLModel):
    id: uuid.UUID
    kind: DecisionKind
    subject: str
    old_value: str | None = None
    new_value: str | None = None
    reason: str | None = None
    decided_by: uuid.UUID | None = None
    decided_by_email: str
    created_at: AwareDatetime


class CallCheckPublic(SQLModel):
    check_type: str
    title: str = Field(description="The check's name; empty for a check since removed")
    check_version: int
    outcome: CheckOutcome
    missing: str | None = Field(
        default=None, description="For a skipped check: what the call's trace lacks"
    )
    ran_at: AwareDatetime


class ChecksRunResult(SQLModel):
    checked: int = Field(description="Stored calls checked by this request")
    remaining: int = Field(description="Stored calls a check has still never run on")


class IssuePublic(SQLModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    check_type: str
    title: str = Field(description="The check's name; empty for a check since removed")
    key: str | None = None
    state: IssueState
    resolved_at: AwareDatetime | None = None
    resolved_version: str | None = None
    finding_count: int
    call_count: int
    first_seen_at: AwareDatetime | None = Field(
        default=None, description="When the earliest call it was found on started"
    )
    last_seen_at: AwareDatetime | None = Field(
        default=None, description="When the latest call it was found on started"
    )
    created_at: AwareDatetime


class IssueFindingPublic(SQLModel):
    id: uuid.UUID
    call_id: uuid.UUID
    call_started_at: AwareDatetime
    check_version: int
    event_ids: list[str]
    detail: dict[str, JsonValue] | None = None
    effect: FindingEffect
    retroactive: bool


class IssueDetailPublic(IssuePublic):
    findings: list[IssueFindingPublic] = Field(
        description="Newest call first; at most 200"
    )


class IssueStateUpdate(SQLModel):
    state: IssueState = Field(description="open, resolved or accepted")
    reason: str | None = Field(
        default=None, max_length=2000, description="Required to accept an issue"
    )
    version: str | None = Field(
        default=None,
        max_length=255,
        description="When resolving: the version that carried the fix",
    )
