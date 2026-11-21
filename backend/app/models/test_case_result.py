import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.run import Run
    from app.models.test_case import TestCase


class TestCaseResultBase(SQLModel):
    run_id: uuid.UUID = Field(
        foreign_key="run.id",
        index=True,
        description="FK to the parent run",
    )
    test_case_id: uuid.UUID = Field(
        foreign_key="test_case.id",
        index=True,
        description="FK to the test case that was executed",
    )
    repetition_index: int = Field(
        default=0,
        description="Which repetition of this test case within a single set pass (0-based)",
    )
    # Transcript
    transcript: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column("transcript", JSONB, nullable=True),
        description="Full conversation transcript as a list of turns",
    )
    turn_count: int | None = Field(
        default=None, description="Total number of conversation turns"
    )
    # What code checks found in the simulated call (`SimulatedFinding`), and the tools
    # that got the default fake. Never production findings.
    check_findings: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column("check_findings", JSONB, nullable=True),
        description="Code-check findings in this simulated call",
    )
    default_fakes: list[str] | None = Field(
        default=None,
        sa_column=Column("default_fakes", JSONB, nullable=True),
        description="Tools the scenario did not fake, answered by the default fake",
    )
    schema_check: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("schema_check", JSONB, nullable=True),
        description="The call's tool arguments checked against the tools' schemas: "
        "the tools with a schema, those unreadable, and each violation. None when "
        "the tested version's schemas could not be read, and for earlier calls",
    )
    agent_token_usage: dict[str, int | bool] | None = Field(
        default=None,
        sa_column=Column("agent_token_usage", JSONB, nullable=True),
        description="Token usage from the agent; may include estimated=true",
    )
    platform_token_usage: dict[str, int] | None = Field(
        default=None,
        sa_column=Column("platform_token_usage", JSONB, nullable=True),
        description="Token usage from the eval platform (simulator + judge)",
    )
    agent_cost_usd: float | None = Field(
        default=None, description="Estimated agent cost in USD for this test case"
    )
    platform_cost_usd: float | None = Field(
        default=None,
        description="Estimated platform cost in USD (simulator + judge) for this test case",
    )
    estimated_cost_usd: float | None = Field(
        default=None, description="Estimated total cost in USD for this test case"
    )
    error_message: str | None = Field(
        default=None, description="Human-readable error message if applicable"
    )
    # Timing
    started_at: datetime | None = Field(
        default=None, description="When test case execution began"
    )
    completed_at: datetime | None = Field(
        default=None, description="When test case execution finished"
    )
    judge_ms: int | None = Field(
        default=None,
        description="How long the judge took; set whenever the judge was asked, "
        "also when it gave no usable answer",
    )
    throttled: int | None = Field(
        default=None,
        description="Times the platform answered 'too many requests' during the call",
    )


class TestCaseResult(TestCaseResultBase, table=True):
    __tablename__ = "test_case_result"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
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

    # Relationships
    run: "Run" = Relationship(back_populates="test_case_results")
    test_case: "TestCase" = Relationship(back_populates="test_case_results")
