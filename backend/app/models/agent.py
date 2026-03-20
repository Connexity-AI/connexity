import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.run import Run


class AgentBase(SQLModel):
    name: str = Field(max_length=255)
    description: str | None = Field(default=None)
    endpoint_url: str = Field(max_length=2048)
    agent_metadata: dict[str, Any] | None = Field(
        default=None, sa_column=Column("metadata", JSONB, nullable=True)
    )


class Agent(AgentBase, table=True):
    __tablename__ = "agent"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"server_default": text("now()"), "onupdate": datetime.now},
    )

    # Relationships
    runs: list["Run"] = Relationship(back_populates="agent")


class AgentCreate(AgentBase):
    pass


class AgentUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    endpoint_url: str | None = Field(default=None, max_length=2048)
    agent_metadata: dict[str, Any] | None = None


class AgentPublic(AgentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class AgentsPublic(SQLModel):
    data: list[AgentPublic]
    count: int
