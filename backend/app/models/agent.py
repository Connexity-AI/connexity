import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, model_validator
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import AgentMode

if TYPE_CHECKING:
    from app.models.agent_version import AgentVersion
    from app.models.prompt_editor import PromptEditorSession
    from app.models.run import Run
    from app.models.test_case import TestCase


def validate_agent_mode_requirements(
    *,
    mode: AgentMode,
    endpoint_url: str | None,
    system_prompt: str | None,
    agent_model: str | None,
) -> None:
    """Raise ValueError if mode-specific required fields are missing."""
    if mode == AgentMode.ENDPOINT:
        if not endpoint_url or not endpoint_url.strip():
            msg = "endpoint_url is required when mode is 'endpoint'"
            raise ValueError(msg)
    elif mode == AgentMode.PLATFORM:
        if not system_prompt or not system_prompt.strip():
            msg = "system_prompt is required when mode is 'platform'"
            raise ValueError(msg)
        if not agent_model or not agent_model.strip():
            msg = "agent_model is required when mode is 'platform'"
            raise ValueError(msg)


class AgentBase(SQLModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(max_length=255, description="Human-readable agent name")
    description: str | None = Field(
        default=None, description="What this agent does and its purpose"
    )
    mode: AgentMode = Field(
        default=AgentMode.ENDPOINT,
        description="endpoint: HTTP agent; platform: LLM simulated on the platform",
    )
    endpoint_url: str | None = Field(
        default=None,
        max_length=2048,
        description="URL of the agent's API endpoint (required when mode=endpoint)",
    )
    system_prompt: str | None = Field(
        default=None,
        description="System prompt for platform agent simulator (required when mode=platform)",
    )
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column("tools", JSONB, nullable=True),
        description="OpenAI-format tool definitions for platform agent simulator",
    )
    agent_model: str | None = Field(
        default=None,
        max_length=255,
        description="LLM model for platform agent simulator (required when mode=platform)",
    )
    agent_provider: str | None = Field(
        default=None,
        max_length=64,
        description="LLM provider for platform agent simulator (e.g. openai, anthropic)",
    )
    agent_temperature: float | None = Field(
        default=None,
        description="Sampling temperature for platform agent simulator (0.0–2.0)",
    )
    agent_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
        description="Arbitrary key-value metadata about the agent",
    )

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "AgentBase":
        # Skip validation for draft agents (all mode-specific fields are None)
        has_any_mode_field = (
            self.endpoint_url is not None
            or self.system_prompt is not None
            or self.agent_model is not None
        )
        if has_any_mode_field:
            validate_agent_mode_requirements(
                mode=self.mode,
                endpoint_url=self.endpoint_url,
                system_prompt=self.system_prompt,
                agent_model=self.agent_model,
            )
        return self


class Agent(AgentBase, table=True):
    __tablename__ = "agent"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    version: int = Field(
        default=1,
        nullable=False,
        description="Current config version number (denormalized; see agent_version history)",
    )
    has_draft: bool = Field(
        default=False,
        nullable=False,
        description="True when an unpublished draft version exists",
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
    runs: list["Run"] = Relationship(
        back_populates="agent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    test_cases: list["TestCase"] = Relationship(back_populates="agent")
    agent_versions: list["AgentVersion"] = Relationship(
        back_populates="agent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    prompt_editor_sessions: list["PromptEditorSession"] = Relationship(
        back_populates="agent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class AgentCreate(AgentBase):
    pass


class AgentCreateDraft(SQLModel):
    name: str = Field(default="Untitled Agent", max_length=255)


class AgentUpdate(SQLModel):
    name: str | None = Field(
        default=None, max_length=255, description="Human-readable agent name"
    )
    description: str | None = Field(
        default=None, description="What this agent does and its purpose"
    )
    mode: AgentMode | None = Field(
        default=None,
        description="endpoint: HTTP agent; platform: LLM simulated on the platform",
    )
    endpoint_url: str | None = Field(
        default=None, max_length=2048, description="URL of the agent's API endpoint"
    )
    system_prompt: str | None = Field(
        default=None,
        description="System prompt for platform agent simulator",
    )
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        description="OpenAI-format tool definitions for platform agent simulator",
    )
    agent_model: str | None = Field(
        default=None,
        max_length=255,
        description="LLM model for platform agent simulator",
    )
    agent_provider: str | None = Field(
        default=None,
        max_length=64,
        description="LLM provider for platform agent simulator",
    )
    agent_temperature: float | None = Field(
        default=None,
        description="Sampling temperature for platform agent simulator (0.0–2.0)",
    )
    agent_metadata: dict[str, Any] | None = Field(
        default=None, description="Arbitrary key-value metadata about the agent"
    )
    change_description: str | None = Field(
        default=None,
        description="Optional changelog when a versionable field changes",
    )


class AgentPublic(AgentBase):
    id: uuid.UUID = Field(description="Unique agent identifier")
    version: int = Field(description="Current behavioral config version")
    has_draft: bool = Field(description="True when an unpublished draft version exists")
    created_at: datetime = Field(description="When the agent was created")
    updated_at: datetime = Field(description="When the agent was last updated")


class AgentsPublic(SQLModel):
    data: list[AgentPublic] = Field(description="List of agents")
    count: int = Field(description="Total number of agents matching the query")
