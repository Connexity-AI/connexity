import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.schemas import ConversationTurn, JudgeVerdict

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
    # Verdict
    verdict: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("verdict", JSONB, nullable=True),
        description="Judge verdict with scores, pass/fail, and reasoning",
    )
    # Metrics
    total_latency_ms: int | None = Field(
        default=None,
        description="Total wall-clock latency for the test case in milliseconds",
    )
    agent_latency_p50_ms: int | None = Field(
        default=None, description="Agent response latency p50 in milliseconds"
    )
    agent_latency_p95_ms: int | None = Field(
        default=None, description="Agent response latency p95 in milliseconds"
    )
    agent_latency_max_ms: int | None = Field(
        default=None,
        description="Maximum agent response latency in milliseconds",
    )
    agent_latency_per_turn_ms: list[int] | None = Field(
        default=None,
        sa_column=Column("agent_latency_per_turn_ms", JSONB, nullable=True),
        description="Per-turn agent response latencies in milliseconds",
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
    # Status
    passed: bool | None = Field(
        default=None, index=True, description="Whether the test case passed evaluation"
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


class TestCaseResult(TestCaseResultBase, table=True):
    __tablename__ = "test_case_result"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
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


class TestCaseResultCreate(SQLModel):
    run_id: uuid.UUID = Field(description="FK to the parent run")
    test_case_id: uuid.UUID = Field(description="FK to the test case that was executed")
    repetition_index: int = Field(
        default=0,
        description="Repetition within one set pass (0-based)",
    )


class TestCaseResultUpdate(SQLModel):
    transcript: list[ConversationTurn] | None = Field(
        default=None,
        description="Full conversation transcript as a list of turns",
    )
    turn_count: int | None = Field(
        default=None, description="Total number of conversation turns"
    )
    verdict: JudgeVerdict | None = Field(
        default=None,
        description="Judge verdict with scores, pass/fail, and reasoning",
    )
    total_latency_ms: int | None = Field(
        default=None,
        description="Total wall-clock latency for the test case in milliseconds",
    )
    agent_latency_p50_ms: int | None = Field(
        default=None, description="Agent response latency p50 in milliseconds"
    )
    agent_latency_p95_ms: int | None = Field(
        default=None, description="Agent response latency p95 in milliseconds"
    )
    agent_latency_max_ms: int | None = Field(
        default=None,
        description="Maximum agent response latency in milliseconds",
    )
    agent_latency_per_turn_ms: list[int] | None = Field(
        default=None,
        description="Per-turn agent response latencies in milliseconds",
    )
    agent_token_usage: dict[str, int | bool] | None = Field(
        default=None,
        description="Token usage from the agent; may include estimated=true",
    )
    platform_token_usage: dict[str, int] | None = Field(
        default=None,
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
    passed: bool | None = Field(
        default=None, description="Whether the test case passed evaluation"
    )
    error_message: str | None = Field(
        default=None, description="Human-readable error message if applicable"
    )
    started_at: datetime | None = Field(
        default=None, description="When test case execution began"
    )
    completed_at: datetime | None = Field(
        default=None, description="When test case execution finished"
    )


class TestCaseResultPublic(SQLModel):
    id: uuid.UUID = Field(description="Unique test case result identifier")
    run_id: uuid.UUID = Field(description="FK to the parent run")
    test_case_id: uuid.UUID = Field(description="FK to the test case that was executed")
    repetition_index: int = Field(
        description="Repetition within one set pass (0-based)",
    )
    transcript: list[ConversationTurn] | None = Field(
        default=None,
        description="Full conversation transcript as a list of turns",
    )
    turn_count: int | None = Field(description="Total number of conversation turns")
    verdict: JudgeVerdict | None = Field(
        default=None,
        description="Judge verdict with scores, pass/fail, and reasoning",
    )
    total_latency_ms: int | None = Field(
        description="Total wall-clock latency for the test case in milliseconds"
    )
    agent_latency_p50_ms: int | None = Field(
        description="Agent response latency p50 in milliseconds"
    )
    agent_latency_p95_ms: int | None = Field(
        description="Agent response latency p95 in milliseconds"
    )
    agent_latency_max_ms: int | None = Field(
        description="Maximum agent response latency in milliseconds"
    )
    agent_latency_per_turn_ms: list[int] | None = Field(
        default=None,
        description="Per-turn agent response latencies in milliseconds",
    )
    agent_token_usage: dict[str, int | bool] | None = Field(
        default=None,
        description="Token usage from the agent; may include estimated=true",
    )
    platform_token_usage: dict[str, int] | None = Field(
        default=None,
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
        description="Estimated total cost in USD for this test case"
    )
    passed: bool | None = Field(description="Whether the test case passed evaluation")
    error_message: str | None = Field(
        description="Human-readable error message if applicable"
    )
    started_at: datetime | None = Field(description="When test case execution began")
    completed_at: datetime | None = Field(
        description="When test case execution finished"
    )
    created_at: datetime = Field(description="When the result was created")
    updated_at: datetime = Field(description="When the result was last updated")


class TestCaseResultsPublic(SQLModel):
    data: list[TestCaseResultPublic] = Field(description="List of test case results")
    count: int = Field(description="Total number of results matching the query")
