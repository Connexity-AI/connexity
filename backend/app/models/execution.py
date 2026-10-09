"""What a backend did to answer a tool call: an execution and its steps.

The words are backend-neutral. n8n is the first backend mapped onto them
(``app.services.mappings.n8n``): an n8n execution is an execution, a node run is a step.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, JsonValue
from sqlalchemy import Column, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import ExecutionMatch, ExecutionStatus


class ExecutionStep(BaseModel):
    """One unit of work inside an execution (an n8n node run)."""

    name: str
    kind: str | None = None
    status: ExecutionStatus = ExecutionStatus.OK
    started_at: AwareDatetime | None = None
    duration_ms: int | None = None
    # A step's input is the output of the steps named here.
    input_from: list[str] = []
    output: JsonValue = None
    error: JsonValue = None
    data_dropped: bool = False


class Execution(BaseModel):
    """One run of a backend workflow, tied to the tool call that triggered it."""

    event_id: str
    provider: str
    external_id: str
    workflow_id: str | None = None
    workflow_name: str | None = None
    workflow_version: str | None = None
    status: ExecutionStatus = ExecutionStatus.UNKNOWN
    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None
    match: ExecutionMatch
    steps: list[ExecutionStep] = []


class CallExecution(SQLModel, table=True):
    __tablename__ = "call_execution"
    __table_args__ = (
        # One execution per tool call. The event is named by its id in the trace, not by
        # its row, because replacing a trace rewrites the event rows.
        UniqueConstraint("call_id", "event_key", name="uq_call_execution_call_event"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    call_id: uuid.UUID = Field(foreign_key="call.id", index=True, ondelete="CASCADE")
    event_key: str = Field(max_length=64, description="The tool call's id in the trace")
    integration_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("integration.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    provider: str = Field(max_length=64)
    external_id: str = Field(max_length=255)
    workflow_id: str | None = Field(default=None, max_length=64)
    workflow_name: str | None = Field(default=None, max_length=255)
    workflow_version: str | None = Field(default=None, max_length=255)
    status: ExecutionStatus = Field(sa_type=enum_type(ExecutionStatus))
    started_at: datetime | None = Field(default=None)
    ended_at: datetime | None = Field(default=None)
    match: ExecutionMatch = Field(sa_type=enum_type(ExecutionMatch))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class CallExecutionStep(SQLModel, table=True):
    __tablename__ = "call_execution_step"
    __table_args__ = (
        UniqueConstraint("execution_id", "seq", name="uq_call_execution_step_seq"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    execution_id: uuid.UUID = Field(
        foreign_key="call_execution.id", index=True, ondelete="CASCADE"
    )
    seq: int = Field(description="Position in the execution, starting at 0")
    name: str = Field(max_length=255)
    kind: str | None = Field(default=None, max_length=255)
    status: ExecutionStatus = Field(sa_type=enum_type(ExecutionStatus))
    started_at: datetime | None = Field(default=None)
    duration_ms: int | None = Field(default=None)
    input_from: list[str] | None = Field(
        default=None, sa_column=Column("input_from", JSONB(none_as_null=True))
    )
    output: Any = Field(
        default=None, sa_column=Column("output", JSONB(none_as_null=True))
    )
    error: Any = Field(
        default=None, sa_column=Column("error", JSONB(none_as_null=True))
    )
    data_dropped: bool = Field(default=False)


class ExecutionSyncResult(SQLModel):
    """What looking for a call's executions found."""

    tool_calls: int = Field(description="Tool calls on the call")
    mapped: int = Field(description="Tool calls whose tool is mapped to a workflow")
    matched: int = Field(description="Tool calls that now have an execution")
    problems: list[str] = []
