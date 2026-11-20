"""Pure Pydantic v2 models for JSONB nested entities.

These are NOT database tables — they serialize into JSONB columns
on the ORM table models (Run, TestCaseResult). Run execution helpers
(:class:`RunConfig`, :class:`UserSimulatorConfig`) live here so services share one
definition.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.models.enums import RunMode, SimulatorMode, TextRuntimeKind, TurnRole

if TYPE_CHECKING:
    pass

# ── Run nested types ───────────────────────────────────────────────


class UserSimulatorConfig(BaseModel):
    """User simulator behavior (LLM persona vs scripted replay) and LLM overrides."""

    mode: SimulatorMode = Field(
        default=SimulatorMode.LLM,
        description="llm: generate via LLM; scripted: replay fixed messages",
    )
    scripted_messages: list[str] = Field(
        default_factory=list,
        description="User lines after first_message, in order (scripted mode only)",
    )
    model: str | None = Field(
        default=None,
        description="Simulator LLM model override",
    )
    provider: str | None = Field(
        default=None,
        description="Simulator LLM provider override",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for simulator LLM",
    )

    @model_validator(mode="after")
    def scripted_mode_requires_messages(self) -> Self:
        if self.mode == SimulatorMode.SCRIPTED and not self.scripted_messages:
            msg = "scripted_messages must be non-empty when mode is 'scripted'"
            raise ValueError(msg)
        return self


# ── Runtime config ────────────────────────────────────────────────


class RetellRuntimeConfig(BaseModel):
    """Retell text runtime.

    Connexity owns the user simulator and judge. The Retell runtime will call
    Retell as the agent side via chat APIs once implemented.
    """

    kind: Literal[TextRuntimeKind.RETELL] = TextRuntimeKind.RETELL
    version: int | None = Field(
        default=None,
        description="The Retell agent version to talk to; none for the latest",
    )


RuntimeConfig = RetellRuntimeConfig


class RunConfig(BaseModel):
    concurrency: int = Field(default=5, description="Max parallel test case executions")
    timeout_per_test_case_ms: int = Field(
        default=120_000,
        description="Timeout per test case in milliseconds before forced stop",
    )
    max_turns: int | None = Field(
        default=None,
        description="Max agent response rounds per test case; null = no cap",
    )
    user_simulator: UserSimulatorConfig | None = Field(
        default=None,
        description=(
            "User simulator: LLM vs scripted replay, model/provider overrides, temperature. "
            "Omitted fields use app LLM defaults."
        ),
    )
    mode: RunMode = Field(
        default=RunMode.TEXT,
        description="Run modality: text today, voice for future realtime simulations.",
    )
    runtime: RuntimeConfig = Field(
        description=(
            "Runtime that drives the eval for the selected mode. Required: evals "
            "always run on the agent's own engine, so there is no default."
        ),
    )


# ── Conversation nested types ──────────────────────────────────────


class ToolCallFunction(BaseModel):
    name: str = Field(description="Tool/function name")
    arguments: str = Field(
        description="JSON-encoded arguments string (OpenAI chat completions convention)"
    )


class ToolCall(BaseModel):
    id: str = Field(
        description="Unique tool call identifier (e.g. call_abc123), OpenAI-compatible"
    )
    type: Literal["function"] = Field(
        default="function", description="Tool call type; only function is supported"
    )
    function: ToolCallFunction = Field(description="Function name and arguments")
    tool_result: Any | None = Field(
        default=None,
        description="Result returned by the tool (platform extension, not in agent wire format)",
    )


class ConversationTurn(BaseModel):
    index: int = Field(description="Zero-based turn index in the conversation")
    role: TurnRole = Field(
        description="Who produced this turn (user, assistant, system, tool)"
    )
    content: str | None = Field(
        default=None,
        description="Text content of the turn; null for tool-call-only assistant turns",
    )
    tool_calls: list[ToolCall] | None = Field(
        default=None, description="Tool calls made during this turn"
    )
    tool_call_id: str | None = Field(
        default=None,
        description="For role=tool turns, references the id of the tool call this message answers",
    )
    latency_ms: int | None = Field(
        default=None, description="Response latency in milliseconds"
    )
    token_count: int | None = Field(
        default=None, description="Token count for this turn"
    )
    timestamp: datetime = Field(description="When this turn occurred")
