import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import AgentMode

if TYPE_CHECKING:
    from app.models.agent import Agent


class AgentVersion(SQLModel, table=True):
    __tablename__ = "agent_version"
    model_config = ConfigDict(use_enum_values=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(
        foreign_key="agent.id",
        index=True,
        nullable=False,
    )
    version: int = Field(nullable=False, description="Monotonic version number per agent")
    mode: AgentMode = Field(
        description="endpoint: HTTP agent; platform: LLM simulated on the platform"
    )
    endpoint_url: str | None = Field(default=None, max_length=2048)
    system_prompt: str | None = Field(default=None)
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column("tools", JSONB, nullable=True),
    )
    agent_model: str | None = Field(default=None, max_length=255)
    agent_provider: str | None = Field(default=None, max_length=64)
    change_description: str | None = Field(default=None)
    created_by: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        index=True,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )

    agent: "Agent" = Relationship(back_populates="agent_versions")


class AgentVersionPublic(SQLModel):
    model_config = ConfigDict(use_enum_values=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    version: int
    mode: AgentMode
    endpoint_url: str | None
    system_prompt: str | None
    tools: list[dict[str, Any]] | None
    agent_model: str | None
    agent_provider: str | None
    change_description: str | None
    created_by: uuid.UUID | None
    created_at: datetime


class AgentVersionsPublic(SQLModel):
    data: list[AgentVersionPublic]
    count: int


class AgentRollbackRequest(SQLModel):
    version: int = Field(ge=1)
    change_description: str | None = None
