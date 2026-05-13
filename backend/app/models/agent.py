import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, model_validator
from sqlalchemy import Column, Enum, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import AgentMode, AgentPromptType, Platform
from app.models.schemas import AggregateMetrics

if TYPE_CHECKING:
    from app.models.agent_version import AgentVersion
    from app.models.eval_config import EvalConfig
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
    platform: Platform | None = Field(
        default=None,
        description=(
            "Voice/agent platform this agent targets. Drives which evaluation "
            "engines are available. Null for legacy rows; use 'webhook' for "
            "custom HTTP agents."
        ),
    )
    prompt_type: AgentPromptType = Field(
        default=AgentPromptType.SINGLE_PROMPT,
        sa_column=Column(
            Enum(
                AgentPromptType,
                values_callable=lambda enum_type: [
                    member.value for member in enum_type
                ],
                native_enum=False,
                validate_strings=True,
                name="agentprompttype",
            ),
            nullable=False,
            server_default=AgentPromptType.SINGLE_PROMPT.value,
        ),
        description="single_prompt: one system prompt; multi_prompt reserved for future use",
    )
    integration_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="integration.id",
        index=True,
        description="Integration used for Retell, Vapi, or ElevenLabs provider agent",
    )
    platform_agent_id: str | None = Field(
        default=None,
        max_length=255,
        description="Provider agent or assistant id when bound to an integration",
    )
    platform_agent_name: str | None = Field(
        default=None,
        max_length=255,
        description="Display name of the provider agent at bind time",
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
    editor_guidelines: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description=(
            "Custom prompting guidelines for the prompt editor agent (None = use built-in default)"
        ),
    )

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "AgentBase":
        # Skip validation for table models (drafts may have incomplete fields)
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
    created_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
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
    calls_last_synced_at: datetime | None = Field(
        default=None,
        nullable=True,
        description=(
            "Stale-while-revalidate marker for Observer. Stamped each time the "
            "GET /calls endpoint kicks off a background Retell sync; gates dedup "
            "and TTL backoff. Operational state, not part of the public API."
        ),
    )

    # Relationships
    runs: list["Run"] = Relationship(
        back_populates="agent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    eval_configs: list["EvalConfig"] = Relationship(
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
    @model_validator(mode="after")
    def validate_mode_fields(self) -> "AgentCreate":
        validate_agent_mode_requirements(
            mode=self.mode,
            endpoint_url=self.endpoint_url,
            system_prompt=self.system_prompt,
            agent_model=self.agent_model,
        )
        return self


class AgentCreateDraft(SQLModel):
    name: str = Field(default="Untitled Agent", max_length=255)
    platform: Platform | None = Field(
        default=None,
        description="When set with integration and platform_agent_id, imports config from provider",
    )
    prompt_type: AgentPromptType = Field(default=AgentPromptType.SINGLE_PROMPT)
    integration_id: uuid.UUID | None = None
    platform_agent_id: str | None = Field(default=None, max_length=255)
    platform_agent_name: str | None = Field(default=None, max_length=255)


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
    platform: Platform | None = Field(
        default=None,
        description="Voice/agent platform this agent targets",
    )
    prompt_type: AgentPromptType | None = None
    integration_id: uuid.UUID | None = None
    platform_agent_id: str | None = Field(default=None, max_length=255)
    platform_agent_name: str | None = Field(default=None, max_length=255)
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
    editor_guidelines: str | None = Field(
        default=None,
        description="Custom prompting guidelines for the prompt editor agent (None = use default)",
    )


class AgentLatestPublishedVersionPublic(SQLModel):
    version: int = Field(description="Active published version number")
    version_name: str | None = Field(default=None)
    version_description: str | None = Field(default=None)


class AgentPublic(AgentBase):
    id: uuid.UUID = Field(description="Unique agent identifier")
    has_draft: bool = Field(description="True when an unpublished draft version exists")
    created_at: datetime = Field(description="When the agent was created")
    updated_at: datetime = Field(description="When the agent was last updated")
    latest_published_version: AgentLatestPublishedVersionPublic | None = Field(
        default=None,
        description="Summary of the active published version for list UI",
    )
    last_eval: "AgentLastEvalSummary | None" = Field(
        default=None,
        description="Latest completed eval run summary for this agent, if any",
    )

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "AgentPublic":
        # Responses mirror persisted rows (drafts, direct DB updates, whitespace-only
        # prompts, etc.). Create/update use AgentCreate / AgentUpdate / Agent with
        # full mode validation.
        return self


class AgentsPublic(SQLModel):
    data: list[AgentPublic] = Field(description="List of agents")
    count: int = Field(description="Total number of agents matching the query")


class AgentLastEvalSummary(SQLModel):
    run_id: uuid.UUID = Field(description="Latest completed run id")
    created_at: datetime = Field(
        description="When the latest completed run was created"
    )
    aggregate_metrics: AggregateMetrics | None = Field(
        default=None,
        description="Aggregate metrics snapshot from the latest completed run",
    )


class AgentGuidelinesPublic(SQLModel):
    guidelines: str = Field(description="Effective guidelines text (custom or default)")
    is_default: bool = Field(
        description="True when using built-in defaults (no custom guidelines stored)"
    )


class AgentGuidelinesUpdate(SQLModel):
    guidelines: str | None = Field(
        default=None,
        description="Custom guidelines text, or null to reset to built-in default",
    )
