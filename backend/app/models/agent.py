import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.run import Run


class AgentBase(SQLModel):
    name: str = Field(max_length=255, description="Human-readable agent name")
    description: str | None = Field(
        default=None, description="What this agent does and its purpose"
    )
    endpoint_url: str = Field(
        max_length=2048, description="URL of the agent's API endpoint"
    )
    agent_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
        description="Arbitrary key-value metadata about the agent",
    )


class Agent(AgentBase, table=True):
    __tablename__ = "agent"

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
    runs: list["Run"] = Relationship(
        back_populates="agent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class AgentCreate(AgentBase):
    pass


class AgentUpdate(SQLModel):
    name: str | None = Field(
        default=None, max_length=255, description="Human-readable agent name"
    )
    description: str | None = Field(
        default=None, description="What this agent does and its purpose"
    )
    endpoint_url: str | None = Field(
        default=None, max_length=2048, description="URL of the agent's API endpoint"
    )
    agent_metadata: dict[str, Any] | None = Field(
        default=None, description="Arbitrary key-value metadata about the agent"
    )


class AgentPublic(AgentBase):
    id: uuid.UUID = Field(description="Unique agent identifier")
    created_at: datetime = Field(description="When the agent was created")
    updated_at: datetime = Field(description="When the agent was last updated")


class AgentsPublic(SQLModel):
    data: list[AgentPublic] = Field(description="List of agents")
    count: int = Field(description="Total number of agents matching the query")
