import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Call(SQLModel, table=True):
    __tablename__ = "call"
    __table_args__ = (
        UniqueConstraint(
            "retell_call_id", "agent_id", name="uq_call_retell_call_agent"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True)
    integration_id: uuid.UUID | None = Field(
        default=None, foreign_key="integration.id", index=True, nullable=True
    )
    retell_call_id: str = Field(max_length=255, index=True)
    retell_agent_id: str = Field(max_length=255, index=True)
    started_at: datetime = Field(index=True)
    duration_seconds: int | None = Field(default=None)
    status: str | None = Field(default=None, max_length=64)
    transcript: list[dict[str, Any]] | None = Field(
        default=None, sa_column=Column("transcript", JSONB, nullable=True)
    )
    raw: dict[str, Any] | None = Field(
        default=None, sa_column=Column("raw", JSONB, nullable=True)
    )
    seen_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class CallPublic(SQLModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    retell_call_id: str
    retell_agent_id: str
    started_at: datetime
    duration_seconds: int | None = None
    status: str | None = None
    transcript: list[dict[str, Any]] | None = None
    is_new: bool = Field(
        default=True,
        description="True when the requesting user has not opened this call yet",
    )
    test_case_count: int = Field(
        default=0, description="Number of test cases sourced from this call"
    )
    created_at: datetime


class CallsPublic(SQLModel):
    data: list[CallPublic]
    count: int


class CallRefreshResult(SQLModel):
    created: int = Field(description="Number of new call rows inserted from Retell")
    total: int = Field(description="Total call rows in DB for this agent after refresh")
