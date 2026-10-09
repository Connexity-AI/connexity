import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.component_version import ServedBy
from app.models.enums import (
    CallChannel,
    CallDirection,
    CallEndReason,
    CallEventType,
    CallLabel,
    Speaker,
    ToolCallStatus,
    TraceCapability,
    TraceSource,
)
from app.models.execution import Execution
from app.models.trace import Trace


class Call(SQLModel, table=True):
    __tablename__ = "call"
    __table_args__ = (
        UniqueConstraint("external_id", "agent_id", name="uq_call_external_id_agent"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True)
    integration_id: uuid.UUID | None = Field(
        default=None, foreign_key="integration.id", index=True, nullable=True
    )
    provider: str = Field(max_length=64, index=True)
    external_id: str = Field(max_length=255, index=True)
    provider_agent_id: str = Field(max_length=255, index=True)
    started_at: datetime = Field(index=True)

    # ── Trace fields (see app.models.trace). Null until a trace is stored. ──
    schema_version: int | None = Field(
        default=None, description="Trace schema version; null when no trace is stored"
    )
    source: TraceSource = Field(
        default=TraceSource.PRODUCTION, index=True, sa_type=enum_type(TraceSource)
    )
    channel: CallChannel | None = Field(
        default=None, nullable=True, sa_type=enum_type(CallChannel)
    )
    direction: CallDirection | None = Field(
        default=None, nullable=True, sa_type=enum_type(CallDirection)
    )
    ended_at: datetime | None = Field(default=None)
    end_reason: CallEndReason | None = Field(
        default=None, nullable=True, index=True, sa_type=enum_type(CallEndReason)
    )
    end_reason_detail: str | None = Field(default=None, max_length=255)
    trace_id: str | None = Field(default=None, max_length=64, index=True)
    agent_number: str | None = Field(default=None, max_length=64)
    caller_number: str | None = Field(default=None, max_length=64, index=True)
    recording_url: str | None = Field(default=None, max_length=2048)
    reports_tool_calls: bool | None = Field(default=None)
    # The agent's own version, and one fingerprint over what every call has (agent,
    # prompt, model), so calls can be grouped by the state that served them.
    agent_version: str | None = Field(default=None, max_length=255)
    state_fingerprint: str | None = Field(default=None, max_length=64, index=True)
    inputs: dict[str, Any] | None = Field(
        default=None, sa_column=Column("inputs", JSONB(none_as_null=True))
    )
    outputs: dict[str, Any] | None = Field(
        default=None, sa_column=Column("outputs", JSONB(none_as_null=True))
    )
    extensions: dict[str, Any] | None = Field(
        default=None, sa_column=Column("extensions", JSONB(none_as_null=True))
    )

    # The provider's original payload, unmodified. Never read as a trace.
    raw: dict[str, Any] | None = Field(
        default=None, sa_column=Column("raw", JSONB, nullable=True)
    )
    seen_at: datetime | None = Field(default=None)
    label: CallLabel | None = Field(
        default=None, nullable=True, sa_type=enum_type(CallLabel)
    )
    deleted_at: datetime | None = Field(default=None, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class CallEvent(SQLModel, table=True):
    """One event of a call's trace. Rows are the only stored form of the timeline."""

    __tablename__ = "call_event"
    __table_args__ = (
        UniqueConstraint("call_id", "seq", name="uq_call_event_call_seq"),
        UniqueConstraint("call_id", "key", name="uq_call_event_call_key"),
        # Tool aggregates: calls, errors and latency per tool.
        Index("ix_call_event_type_name", "type", "name"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    call_id: uuid.UUID = Field(foreign_key="call.id", index=True, ondelete="CASCADE")
    seq: int = Field(description="Position in the call, starting at 0")
    key: str = Field(max_length=64, description="The event's id in the wire format")
    type: CallEventType = Field(sa_type=enum_type(CallEventType))
    start_ms: int | None = Field(default=None)
    end_ms: int | None = Field(default=None)
    span_id: str | None = Field(default=None, max_length=64)

    # utterance
    speaker: Speaker | None = Field(
        default=None, nullable=True, sa_type=enum_type(Speaker)
    )
    text: str | None = Field(default=None, sa_column=Column("text", Text))
    interrupted: bool | None = Field(default=None)

    # tool_call and marker
    name: str | None = Field(default=None, max_length=255)

    # tool_call
    status: ToolCallStatus | None = Field(
        default=None, nullable=True, sa_type=enum_type(ToolCallStatus)
    )
    arguments: dict[str, Any] | None = Field(
        default=None, sa_column=Column("arguments", JSONB(none_as_null=True))
    )
    # Any JSON value; a JSON null result is stored as SQL NULL.
    result: Any = Field(
        default=None, sa_column=Column("result", JSONB(none_as_null=True))
    )

    # marker
    detail: dict[str, Any] | None = Field(
        default=None, sa_column=Column("detail", JSONB(none_as_null=True))
    )


class CallComponent(SQLModel, table=True):
    """One thing that served a call, with the version that was live."""

    __tablename__ = "call_component"
    __table_args__ = (
        UniqueConstraint("call_id", "seq", name="uq_call_component_call_seq"),
        # Calls grouped by the version of a component.
        Index("ix_call_component_kind_ref_version", "kind", "ref", "version"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    call_id: uuid.UUID = Field(foreign_key="call.id", index=True, ondelete="CASCADE")
    seq: int = Field(description="Position in the trace's component list")
    kind: str = Field(max_length=64)
    name: str = Field(max_length=255)
    ref: str | None = Field(default=None, max_length=255)
    version: str | None = Field(default=None, max_length=255)
    fingerprint: str | None = Field(default=None, max_length=255)


class CallPublic(SQLModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    provider: str
    external_id: str
    provider_agent_id: str
    source: TraceSource
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int | None = Field(
        default=None, description="Derived from started_at and ended_at"
    )
    end_reason: CallEndReason | None = None
    end_reason_detail: str | None = None
    agent_version: str | None = None
    state_fingerprint: str | None = Field(
        default=None,
        description="One fingerprint over the agent, prompt and model that served it",
    )
    has_trace: bool = Field(
        description="False when the call was synced but not yet converted to a trace"
    )
    is_new: bool = Field(
        default=True,
        description="True when the requesting user has not opened this call yet",
    )
    test_case_count: int = Field(
        default=0, description="Number of test cases sourced from this call"
    )
    label: CallLabel | None = None
    created_at: datetime


class CallTracePublic(SQLModel):
    trace: Trace
    capabilities: list[TraceCapability]
    # What the backend did for each tool call that has a known execution.
    executions: list[Execution] = []
    # What served the call: the trace's components, and a skill for each workflow that
    # ran, each with the catalogue entry that holds its content when there is one.
    served_by: list[ServedBy] = []


class CallsPublic(SQLModel):
    data: list[CallPublic]
    count: int


class CallLabelUpdate(SQLModel):
    label: CallLabel | None = None


class CallRefreshResult(SQLModel):
    created: int = Field(description="Number of new calls stored by this refresh")
    total: int = Field(description="Total call rows in DB for this agent after refresh")
