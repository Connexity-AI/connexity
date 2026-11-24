import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict
from sqlalchemy import Column, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.columns import enum_type
from app.models.enums import AgentMode, Platform

if TYPE_CHECKING:
    from app.models.eval_config import EvalConfig
    from app.models.run import Run
    from app.models.test_case import TestCase


class AgentBase(SQLModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(max_length=255, description="Human-readable agent name")
    description: str | None = Field(
        default=None, description="What this agent does and its purpose"
    )
    mode: AgentMode = Field(
        default=AgentMode.PLATFORM,
        sa_type=enum_type(AgentMode),
        description="platform: the agent runs on a voice platform",
    )
    platform: Platform | None = Field(
        default=None,
        sa_type=enum_type(Platform),
        description="Voice platform the agent runs on",
    )
    integration_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="integration.id",
        index=True,
        description="Integration used for Retell, Vapi, or ElevenLabs provider agent",
    )
    platform_agent_id: str | None = Field(
        default=None,
        max_length=255,
        description="Provider agent or assistant id when bound to an integration",
    )
    platform_agent_name: str | None = Field(
        default=None,
        max_length=255,
        description="Display name of the provider agent at bind time",
    )
    agent_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
        description="Arbitrary key-value metadata about the agent",
    )


class Agent(AgentBase, table=True):
    __tablename__ = "agent"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    created_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={
            "server_default": text("now()"),
            "onupdate": lambda: datetime.now(UTC),
        },
    )
    calls_last_synced_at: datetime | None = Field(
        default=None,
        nullable=True,
        description=(
            "Stale-while-revalidate marker for Observer. Stamped each time the "
            "GET /calls endpoint kicks off a background Retell sync; gates dedup "
            "and TTL backoff. Operational state, not part of the public API."
        ),
    )

    # The first scan: the agent's past calls, pulled once in steps (see
    # `app/services/first_scan.py`). Empty until the first step lists the window.
    scan_from: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        description="Start of the first scan's window",
    )
    scan_until: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        description="End of the first scan's window; later calls come by webhook",
    )
    scan_total: int | None = Field(
        default=None, description="Finished calls the platform listed in the window"
    )
    scan_cursor: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        description="Start time of the last call the first scan has dealt with",
    )
    scan_done_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        description="When the first scan of this agent finished",
    )
    scan_window_total: int | None = Field(
        default=None,
        description="Calls the window held before the included first scan's limit "
        "cut it; unset when no limit applied",
    )
    # Set when the agent's workspace was deleted. The row stays with its name only, so
    # kept usage totals still name the agent.
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )

    # Relationships
    runs: list["Run"] = Relationship(
        back_populates="agent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    eval_configs: list["EvalConfig"] = Relationship(
        back_populates="agent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    test_cases: list["TestCase"] = Relationship(back_populates="agent")
