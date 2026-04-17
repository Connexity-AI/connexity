import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.agent_version import AgentVersion
from app.models.enums import RunStatus
from app.models.schemas import AggregateMetrics, RunConfig

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.eval_config import EvalConfig
    from app.models.test_case_result import TestCaseResult


class RunBase(SQLModel):
    name: str | None = Field(
        default=None, max_length=255, description="Optional human-readable run label"
    )
    # Agent snapshot (captured at run time)
    agent_id: uuid.UUID = Field(
        foreign_key="agent.id",
        index=True,
        description="FK to the agent being evaluated",
    )
    agent_endpoint_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Agent endpoint URL snapshot (required for endpoint-mode agents)",
    )
    agent_system_prompt: str | None = Field(
        default=None,
        description="Agent system prompt snapshot captured at run start",
    )
    agent_tools: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column("agent_tools", JSONB, nullable=True),
        description="Agent tool definitions snapshot captured at run start",
    )
    agent_mode: str | None = Field(
        default=None,
        max_length=32,
        description="Agent mode snapshot: endpoint or platform",
    )
    agent_model: str | None = Field(
        default=None,
        max_length=255,
        description="Effective LLM model for platform agent simulator for this run",
    )
    agent_provider: str | None = Field(
        default=None,
        max_length=64,
        description="Effective LLM provider for platform agent simulator for this run",
    )
    # Eval config
    eval_config_id: uuid.UUID = Field(
        foreign_key="eval_config.id",
        index=True,
        description="FK to the eval config executed in this run",
    )
    eval_config_version: int = Field(
        default=1,
        description="Version of the eval config at run time",
    )
    agent_version: int | None = Field(
        default=None,
        index=True,
        description="Agent behavioral config version at run creation",
    )
    agent_version_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="agent_version.id",
        index=True,
        description="FK to immutable agent_version row at run creation",
    )
    # Config
    config: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("config", JSONB, nullable=True),
        description="Run configuration (judge model, concurrency, timeouts, etc.)",
    )
    # Status
    status: RunStatus = Field(
        default=RunStatus.PENDING,
        index=True,
        description="Current execution status of the run",
    )
    is_baseline: bool = Field(
        default=False,
        index=True,
        description="Whether this run is marked as the baseline for comparison",
    )
    # Aggregate metrics (populated after completion)
    aggregate_metrics: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("aggregate_metrics", JSONB, nullable=True),
        description="Aggregate pass rate, latency, cost metrics computed after completion",
    )
    # Timing
    started_at: datetime | None = Field(
        default=None, description="When the run began executing"
    )
    completed_at: datetime | None = Field(
        default=None, description="When the run finished (success or failure)"
    )


class Run(RunBase, table=True):
    __tablename__ = "run"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_by: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        index=True,
        description="User who created the run; used to resolve custom judge metrics",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
        index=True,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={
            "server_default": text("now()"),
            "onupdate": lambda: datetime.now(UTC),
        },
    )

    # Relationships
    agent: "Agent" = Relationship(back_populates="runs")
    agent_version_row: AgentVersion | None = Relationship()
    eval_config: "EvalConfig" = Relationship(back_populates="runs")
    test_case_results: list["TestCaseResult"] = Relationship(
        back_populates="run",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class RunCreate(SQLModel):
    name: str | None = Field(
        default=None, description="Optional human-readable run label"
    )
    agent_id: uuid.UUID = Field(description="FK to the agent being evaluated")
    agent_endpoint_url: str | None = Field(
        default=None,
        description="Agent endpoint URL snapshot captured at run start",
    )
    agent_system_prompt: str | None = Field(
        default=None,
        description="Agent system prompt snapshot captured at run start",
    )
    agent_tools: list[dict[str, Any]] | None = Field(
        default=None,
        description="Agent tool definitions snapshot captured at run start",
    )
    agent_mode: str | None = Field(
        default=None,
        description="Agent mode snapshot: endpoint or platform",
    )
    agent_model: str | None = Field(
        default=None,
        description="Effective LLM model for platform agent simulator for this run",
    )
    agent_provider: str | None = Field(
        default=None,
        description="Effective LLM provider for platform agent simulator for this run",
    )
    eval_config_id: uuid.UUID = Field(description="FK to the eval config to execute")
    eval_config_version: int = Field(
        default=1, description="Version of the eval config at run time"
    )
    agent_version: int | None = Field(
        default=None,
        description="Agent behavioral config version at run creation (set by server)",
    )
    agent_version_id: uuid.UUID | None = Field(
        default=None,
        description="FK to agent_version row at run creation (set by server)",
    )
    config: RunConfig | None = Field(
        default=None,
        description="Run configuration (judge model, concurrency, timeouts, etc.)",
    )
    is_baseline: bool = Field(
        default=False,
        description="Whether this run is marked as the baseline for comparison",
    )


class RunUpdate(SQLModel):
    name: str | None = Field(
        default=None, description="Optional human-readable run label"
    )
    status: RunStatus | None = Field(
        default=None, description="Current execution status of the run"
    )
    is_baseline: bool | None = Field(
        default=None,
        description="Whether this run is marked as the baseline for comparison",
    )
    aggregate_metrics: AggregateMetrics | None = Field(
        default=None,
        description="Aggregate metrics computed after completion",
    )
    started_at: datetime | None = Field(
        default=None, description="When the run began executing"
    )
    completed_at: datetime | None = Field(
        default=None, description="When the run finished (success or failure)"
    )


class RunPublic(SQLModel):
    id: uuid.UUID = Field(description="Unique run identifier")
    created_by: uuid.UUID | None = Field(
        default=None,
        description="User who created the run; used to resolve custom judge metrics",
    )
    name: str | None = Field(description="Optional human-readable run label")
    agent_id: uuid.UUID = Field(description="FK to the agent being evaluated")
    agent_endpoint_url: str | None = Field(
        default=None,
        description="Agent endpoint URL snapshot captured at run start",
    )
    agent_system_prompt: str | None = Field(
        default=None,
        description="Agent system prompt snapshot captured at run start",
    )
    agent_mode: str | None = Field(
        default=None,
        description="Agent mode snapshot: endpoint or platform",
    )
    agent_model: str | None = Field(
        default=None,
        description="Effective LLM model for platform agent simulator for this run",
    )
    agent_provider: str | None = Field(
        default=None,
        description="Effective LLM provider for platform agent simulator for this run",
    )
    eval_config_id: uuid.UUID = Field(
        description="FK to the eval config executed in this run"
    )
    eval_config_version: int = Field(
        description="Version of the eval config at run time"
    )
    agent_version: int | None = Field(
        default=None,
        description="Agent behavioral config version at run creation",
    )
    config: RunConfig | None = Field(
        default=None,
        description="Run configuration (judge model, concurrency, timeouts, etc.)",
    )
    status: RunStatus = Field(description="Current execution status of the run")
    is_baseline: bool = Field(
        description="Whether this run is marked as the baseline for comparison"
    )
    aggregate_metrics: AggregateMetrics | None = Field(
        default=None,
        description="Aggregate metrics computed after completion",
    )
    started_at: datetime | None = Field(description="When the run began executing")
    completed_at: datetime | None = Field(
        description="When the run finished (success or failure)"
    )
    created_at: datetime = Field(description="When the run was created")
    updated_at: datetime = Field(description="When the run was last updated")


class RunsPublic(SQLModel):
    data: list[RunPublic] = Field(description="List of runs")
    count: int = Field(description="Total number of runs matching the query")
