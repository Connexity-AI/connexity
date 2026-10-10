"""Findings, the decisions that govern checks, and when each check first existed.

The model is the vision's section 7. A check itself is code (``app.services.checks``),
not a row.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import AwareDatetime, JsonValue
from sqlalchemy import Column, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import CheckKind, CheckMode, DecisionKind, FindingEffect

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
