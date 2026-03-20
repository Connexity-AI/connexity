import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import RunStatus
from app.models.schemas import AggregateMetrics, RunConfig

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.scenario_result import ScenarioResult
    from app.models.scenario_set import ScenarioSet


class RunBase(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    # Agent snapshot (captured at run time)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True)
    agent_endpoint_url: str = Field(max_length=2048)
    agent_system_prompt: str | None = Field(default=None)
    agent_tools: list[dict[str, Any]] | None = Field(
        default=None, sa_column=Column("agent_tools", JSONB, nullable=True)
    )
    prompt_version: str | None = Field(default=None, max_length=100)
    prompt_snapshot: str | None = Field(default=None)
    tools_snapshot: list[dict[str, Any]] | None = Field(
        default=None, sa_column=Column("tools_snapshot", JSONB, nullable=True)
    )
    tools_snapshot_hash: str | None = Field(default=None, max_length=64)
    # Scenario set
    scenario_set_id: uuid.UUID = Field(foreign_key="scenario_set.id", index=True)
    scenario_set_version: int = Field(default=1)
    # Config
    config: dict[str, Any] | None = Field(
        default=None, sa_column=Column("config", JSONB, nullable=True)
    )
    # Status
    status: RunStatus = Field(default=RunStatus.PENDING, index=True)
    is_baseline: bool = Field(default=False, index=True)
    # Aggregate metrics (populated after completion)
    aggregate_metrics: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("aggregate_metrics", JSONB, nullable=True),
    )
    # Timing
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)


class Run(RunBase, table=True):
    __tablename__ = "run"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"server_default": text("now()")},
        index=True,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"server_default": text("now()"), "onupdate": datetime.now},
    )

    # Relationships
    agent: "Agent" = Relationship(back_populates="runs")
    scenario_set: "ScenarioSet" = Relationship(back_populates="runs")
    scenario_results: list["ScenarioResult"] = Relationship(back_populates="run")


class RunCreate(SQLModel):
    name: str | None = None
    agent_id: uuid.UUID
    agent_endpoint_url: str
    agent_system_prompt: str | None = None
    agent_tools: list[dict[str, Any]] | None = None
    prompt_version: str | None = None
    prompt_snapshot: str | None = None
    tools_snapshot: list[dict[str, Any]] | None = None
    tools_snapshot_hash: str | None = None
    scenario_set_id: uuid.UUID
    scenario_set_version: int = 1
    config: RunConfig | None = None
    is_baseline: bool = False


class RunUpdate(SQLModel):
    name: str | None = None
    status: RunStatus | None = None
    is_baseline: bool | None = None
    aggregate_metrics: AggregateMetrics | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RunPublic(SQLModel):
    id: uuid.UUID
    name: str | None
    agent_id: uuid.UUID
    agent_endpoint_url: str
    agent_system_prompt: str | None
    scenario_set_id: uuid.UUID
    scenario_set_version: int
    config: RunConfig | None = None
    status: RunStatus
    is_baseline: bool
    aggregate_metrics: AggregateMetrics | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RunsPublic(SQLModel):
    data: list[RunPublic]
    count: int
