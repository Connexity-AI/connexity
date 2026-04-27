import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.schemas import RunConfig

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.run import Run
    from app.models.test_case import TestCase


class EvalConfigMember(SQLModel, table=True):
    """Many-to-many join table between EvalConfig and TestCase."""

    __tablename__ = "eval_config_member"

    eval_config_id: uuid.UUID = Field(
        foreign_key="eval_config.id",
        primary_key=True,
        index=True,
        description="FK to the parent eval config",
    )
    test_case_id: uuid.UUID = Field(
        foreign_key="test_case.id",
        primary_key=True,
        description="FK to the linked test case",
    )
    position: int = Field(
        default=0, description="Sort order of the test case within the config"
    )
    repetitions: int = Field(
        default=1,
        ge=1,
        description="How many times to execute this test case per run",
    )

    # Relationships
    eval_config: "EvalConfig" = Relationship(back_populates="test_case_links")
    test_case: "TestCase" = Relationship(back_populates="eval_config_links")


class EvalConfigMemberEntry(SQLModel):
    """API payload for adding or replacing config members with per-test-case repetition counts."""

    test_case_id: uuid.UUID = Field(description="Test case to include in the config")
    repetitions: int = Field(
        default=1,
        ge=1,
        description="How many times to execute this test case per run",
    )


class EvalConfigMemberPublic(SQLModel):
    """Public view of one test case's membership in a config."""

    test_case_id: uuid.UUID = Field(description="Linked test case id")
    position: int = Field(description="Order within the config")
    repetitions: int = Field(ge=1, description="Executions per run for this test case")


class EvalConfigMembersPublic(SQLModel):
    data: list[EvalConfigMemberPublic] = Field(
        description="Config members with position and repetitions"
    )
    count: int = Field(description="Total members matching the query")


class EvalConfigBase(SQLModel):
    name: str = Field(
        max_length=255, index=True, description="Human-readable config name"
    )
    description: str | None = Field(
        default=None, description="What this eval config covers"
    )
    agent_id: uuid.UUID = Field(
        foreign_key="agent.id",
        index=True,
        description="Agent this eval config belongs to",
    )
    version: int = Field(
        default=1,
        description="Monotonically increasing version for snapshot tracking",
    )


class EvalConfig(EvalConfigBase, table=True):
    __tablename__ = "eval_config"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    config: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("config", JSONB, nullable=True),
        description="Run configuration (concurrency, max_turns, judge, tool_mode, etc.)",
    )
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
    agent: "Agent" = Relationship(back_populates="eval_configs")
    test_case_links: list[EvalConfigMember] = Relationship(
        back_populates="eval_config",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    runs: list["Run"] = Relationship(back_populates="eval_config")


class EvalConfigCreate(SQLModel):
    name: str = Field(max_length=255, description="Human-readable config name")
    description: str | None = Field(
        default=None, description="What this eval config covers"
    )
    agent_id: uuid.UUID = Field(description="Agent this eval config belongs to")
    config: RunConfig | None = Field(
        default=None,
        description="Run configuration (concurrency, max_turns, judge, tool_mode, etc.)",
    )
    members: list[EvalConfigMemberEntry] | None = Field(
        default=None,
        description="Initial members with per-test-case repetitions (omit or empty for none)",
    )


class EvalConfigUpdate(SQLModel):
    name: str | None = Field(default=None, description="Human-readable config name")
    description: str | None = Field(
        default=None, description="What this eval config covers"
    )
    config: RunConfig | None = Field(
        default=None,
        description="Run configuration (concurrency, max_turns, judge, tool_mode, etc.)",
    )


class EvalConfigPublic(EvalConfigBase):
    id: uuid.UUID = Field(description="Unique eval config identifier")
    config: RunConfig | None = Field(
        default=None,
        description="Run configuration (concurrency, max_turns, judge, tool_mode, etc.)",
    )
    test_case_count: int = 0
    effective_test_case_count: int = Field(
        default=0,
        description="Sum of per-test-case repetitions — total expanded executions",
    )
    total_runs: int = Field(
        default=0, description="Total number of runs for this eval config"
    )
    created_at: datetime = Field(description="When the config was created")
    updated_at: datetime = Field(description="When the config was last updated")


class EvalConfigsPublic(SQLModel):
    data: list[EvalConfigPublic] = Field(description="List of eval configs")
    count: int = Field(description="Total number of configs matching the query")


class EvalConfigMembersUpdate(SQLModel):
    members: list[EvalConfigMemberEntry]
