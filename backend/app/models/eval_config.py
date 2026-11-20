import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.run import Run
    from app.models.test_case import TestCase


class EvalConfigMember(SQLModel, table=True):
    """Many-to-many join table between EvalConfig and TestCase."""

    __tablename__ = "eval_config_member"

    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
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
    # Relationships
    eval_config: "EvalConfig" = Relationship(back_populates="test_case_links")
    test_case: "TestCase" = Relationship(back_populates="eval_config_links")


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
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    config: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("config", JSONB, nullable=True),
        description="Not used by scenario sets",
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
    deleted_at: datetime | None = Field(default=None, index=True)

    # Relationships
    agent: "Agent" = Relationship(back_populates="eval_configs")
    test_case_links: list[EvalConfigMember] = Relationship(
        back_populates="eval_config",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    runs: list["Run"] = Relationship(back_populates="eval_config")
