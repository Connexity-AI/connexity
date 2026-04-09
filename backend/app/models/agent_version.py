import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict
from sqlalchemy import Column, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import AgentMode, AgentVersionStatus

if TYPE_CHECKING:
    from app.models.agent import Agent


class AgentVersion(SQLModel, table=True):
    __tablename__ = "agent_version"
    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "version",
            name="uq_agent_version_agent_version",
        ),
        Index(
            "ix_agent_version_one_draft_per_agent",
            "agent_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
    )
    model_config = ConfigDict(use_enum_values=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(
        foreign_key="agent.id",
        index=True,
        nullable=False,
    )
    version: int | None = Field(
        default=None,
        nullable=True,
        description="Monotonic version number; NULL for drafts",
    )
    status: AgentVersionStatus = Field(
        default=AgentVersionStatus.PUBLISHED,
        nullable=False,
        description="draft or published",
    )
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
    agent_temperature: float | None = Field(default=None)
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
    version: int | None
    status: AgentVersionStatus
    mode: AgentMode
    endpoint_url: str | None
    system_prompt: str | None
    tools: list[dict[str, Any]] | None
    agent_model: str | None
    agent_provider: str | None
    agent_temperature: float | None
    change_description: str | None
    created_by: uuid.UUID | None
    created_at: datetime


class AgentVersionsPublic(SQLModel):
    data: list[AgentVersionPublic]
    count: int


class AgentRollbackRequest(SQLModel):
    version: int = Field(ge=1)
    change_description: str | None = None


class AgentDraftUpdate(SQLModel):
    """Partial update for versionable agent fields — used by PUT /agents/{id}/draft."""

    mode: AgentMode | None = None
    endpoint_url: str | None = None
    system_prompt: str | None = None
    tools: list[dict[str, Any]] | None = None
    agent_model: str | None = None
    agent_provider: str | None = None
    agent_temperature: float | None = None


class PublishRequest(SQLModel):
    change_description: str | None = None
