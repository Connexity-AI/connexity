import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import ErrorCategory
from app.models.schemas import ConversationTurn, JudgeVerdict

if TYPE_CHECKING:
    from app.models.run import Run
    from app.models.scenario import Scenario


class ScenarioResultBase(SQLModel):
    run_id: uuid.UUID = Field(
        foreign_key="run.id",
        index=True,
        description="FK to the parent run",
    )
    scenario_id: uuid.UUID = Field(
        foreign_key="scenario.id",
        index=True,
        description="FK to the scenario that was executed",
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
        description="Total wall-clock latency for the scenario in milliseconds",
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
    agent_token_usage: dict[str, int] | None = Field(
        default=None,
        sa_column=Column("agent_token_usage", JSONB, nullable=True),
        description="Token usage breakdown from the agent (input/output counts)",
    )
    platform_token_usage: dict[str, int] | None = Field(
        default=None,
        sa_column=Column("platform_token_usage", JSONB, nullable=True),
        description="Token usage from the eval platform (simulator + judge)",
    )
    estimated_cost_usd: float | None = Field(
        default=None, description="Estimated total cost in USD for this scenario"
    )
    # Status
    passed: bool | None = Field(
        default=None, index=True, description="Whether the scenario passed evaluation"
    )
    error_category: ErrorCategory = Field(
        default=ErrorCategory.NONE,
        index=True,
        description="Classified error category if the scenario failed",
    )
    error_message: str | None = Field(
        default=None, description="Human-readable error message if applicable"
    )
    # Timing
    started_at: datetime | None = Field(
        default=None, description="When scenario execution began"
    )
    completed_at: datetime | None = Field(
        default=None, description="When scenario execution finished"
    )


class ScenarioResult(ScenarioResultBase, table=True):
    __tablename__ = "scenario_result"

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
    run: "Run" = Relationship(back_populates="scenario_results")
    scenario: "Scenario" = Relationship(back_populates="scenario_results")


class ScenarioResultCreate(SQLModel):
    run_id: uuid.UUID = Field(description="FK to the parent run")
    scenario_id: uuid.UUID = Field(description="FK to the scenario that was executed")


class ScenarioResultUpdate(SQLModel):
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
        description="Total wall-clock latency for the scenario in milliseconds",
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
    agent_token_usage: dict[str, int] | None = Field(
        default=None,
        description="Token usage breakdown from the agent (input/output counts)",
    )
    platform_token_usage: dict[str, int] | None = Field(
        default=None,
        description="Token usage from the eval platform (simulator + judge)",
    )
    estimated_cost_usd: float | None = Field(
        default=None, description="Estimated total cost in USD for this scenario"
    )
    passed: bool | None = Field(
        default=None, description="Whether the scenario passed evaluation"
    )
    error_category: ErrorCategory | None = Field(
        default=None,
        description="Classified error category if the scenario failed",
    )
    error_message: str | None = Field(
        default=None, description="Human-readable error message if applicable"
    )
    started_at: datetime | None = Field(
        default=None, description="When scenario execution began"
    )
    completed_at: datetime | None = Field(
        default=None, description="When scenario execution finished"
    )


class ScenarioResultPublic(SQLModel):
    id: uuid.UUID = Field(description="Unique scenario result identifier")
    run_id: uuid.UUID = Field(description="FK to the parent run")
    scenario_id: uuid.UUID = Field(description="FK to the scenario that was executed")
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
        description="Total wall-clock latency for the scenario in milliseconds"
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
    agent_token_usage: dict[str, int] | None = Field(
        default=None,
        description="Token usage breakdown from the agent (input/output counts)",
    )
    platform_token_usage: dict[str, int] | None = Field(
        default=None,
        description="Token usage from the eval platform (simulator + judge)",
    )
    estimated_cost_usd: float | None = Field(
        description="Estimated total cost in USD for this scenario"
    )
    passed: bool | None = Field(description="Whether the scenario passed evaluation")
    error_category: ErrorCategory = Field(
        description="Classified error category if the scenario failed"
    )
    error_message: str | None = Field(
        description="Human-readable error message if applicable"
    )
    started_at: datetime | None = Field(description="When scenario execution began")
    completed_at: datetime | None = Field(
        description="When scenario execution finished"
    )
    created_at: datetime = Field(description="When the result was created")
    updated_at: datetime = Field(description="When the result was last updated")


class ScenarioResultsPublic(SQLModel):
    data: list[ScenarioResultPublic] = Field(description="List of scenario results")
    count: int = Field(description="Total number of results matching the query")
