import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.columns import enum_type
from app.models.enums import RunScope, RunStatus

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.eval_config import EvalConfig
    from app.models.test_case_result import TestCaseResult


class RunBase(SQLModel):
    agent_id: uuid.UUID = Field(
        foreign_key="agent.id",
        index=True,
        description="The agent the run tests",
    )
    agent_mode: str | None = Field(
        default=None,
        max_length=32,
        description="Agent mode snapshot: endpoint or platform",
    )
    eval_config_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="eval_config.id",
        index=True,
        description="The set of scenarios run; empty for a pick or every scenario",
    )
    # What the run covers (`plans/2026-11-17-text-runner.md`).
    scope: RunScope | None = Field(
        default=None,
        sa_type=enum_type(RunScope),
        description="A named set, a pick of scenarios, or every scenario",
    )
    set_name: str | None = Field(
        default=None, max_length=255, description="The set's name when it was run"
    )
    repeats: int | None = Field(
        default=None, description="How many times each scenario runs"
    )
    spec_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="spec.id",
        ondelete="SET NULL",
        description="The spec version whose rules the run judges",
    )
    assistant_name: str | None = Field(
        default=None,
        max_length=255,
        description="The assistant that started the run for the person",
    )
    session_name: str | None = Field(
        default=None,
        max_length=40,
        description="The name the assistant gave its session, when it gave one",
    )
    platform_version: str | None = Field(
        default=None,
        max_length=64,
        description="The agent's version on its platform that the run tests",
    )
    version_fingerprint: str | None = Field(
        default=None,
        max_length=64,
        description="Fingerprint of the tested version's content, read when the run "
        "starts; an unpublished version is edited under the same number",
    )
    status_detail: str | None = Field(
        default=None,
        max_length=1024,
        description="Why the run failed or stopped",
    )
    # Config
    config: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("config", JSONB, nullable=True),
        description="Run configuration (concurrency, timeouts, simulated caller)",
    )
    # Status
    status: RunStatus = Field(
        default=RunStatus.PENDING,
        index=True,
        sa_type=enum_type(RunStatus),
        description="Current execution status of the run",
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
    __table_args__ = (
        # A run always says which version it tested (Dmytro, 2026-11-19).
        CheckConstraint(
            "scope IS NULL OR platform_version IS NOT NULL",
            name="ck_run_scenarios_have_a_version",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    created_by: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        index=True,
        description="User who started the run",
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
    eval_config: "EvalConfig" = Relationship(back_populates="runs")
    test_case_results: list["TestCaseResult"] = Relationship(
        back_populates="run",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
