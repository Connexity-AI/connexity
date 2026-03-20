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
    run_id: uuid.UUID = Field(foreign_key="run.id", index=True)
    scenario_id: uuid.UUID = Field(foreign_key="scenario.id", index=True)
    # Transcript
    transcript: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column("transcript", JSONB, nullable=True),
    )
    turn_count: int | None = Field(default=None)
    # Verdict
    verdict: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("verdict", JSONB, nullable=True),
    )
    # Metrics
    total_latency_ms: int | None = Field(default=None)
    agent_latency_p50_ms: int | None = Field(default=None)
    agent_latency_p95_ms: int | None = Field(default=None)
    agent_latency_max_ms: int | None = Field(default=None)
    agent_token_usage: dict[str, int] | None = Field(
        default=None,
        sa_column=Column("agent_token_usage", JSONB, nullable=True),
    )
    platform_token_usage: dict[str, int] | None = Field(
        default=None,
        sa_column=Column("platform_token_usage", JSONB, nullable=True),
    )
    estimated_cost_usd: float | None = Field(default=None)
    # Status
    passed: bool | None = Field(default=None, index=True)
    error_category: ErrorCategory = Field(default=ErrorCategory.NONE, index=True)
    error_message: str | None = Field(default=None)
    # Timing
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)


class ScenarioResult(ScenarioResultBase, table=True):
    __tablename__ = "scenario_result"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()"), "onupdate": datetime.now},
    )

    # Relationships
    run: "Run" = Relationship(back_populates="scenario_results")
    scenario: "Scenario" = Relationship(back_populates="scenario_results")


class ScenarioResultCreate(SQLModel):
    run_id: uuid.UUID
    scenario_id: uuid.UUID


class ScenarioResultUpdate(SQLModel):
    transcript: list[ConversationTurn] | None = None
    turn_count: int | None = None
    verdict: JudgeVerdict | None = None
    total_latency_ms: int | None = None
    agent_latency_p50_ms: int | None = None
    agent_latency_p95_ms: int | None = None
    agent_latency_max_ms: int | None = None
    agent_token_usage: dict[str, int] | None = None
    platform_token_usage: dict[str, int] | None = None
    estimated_cost_usd: float | None = None
    passed: bool | None = None
    error_category: ErrorCategory | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ScenarioResultPublic(SQLModel):
    id: uuid.UUID
    run_id: uuid.UUID
    scenario_id: uuid.UUID
    transcript: list[ConversationTurn] | None = None
    turn_count: int | None
    verdict: JudgeVerdict | None = None
    total_latency_ms: int | None
    agent_latency_p50_ms: int | None
    agent_latency_p95_ms: int | None
    agent_latency_max_ms: int | None
    estimated_cost_usd: float | None
    passed: bool | None
    error_category: ErrorCategory
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ScenarioResultsPublic(SQLModel):
    data: list[ScenarioResultPublic]
    count: int
