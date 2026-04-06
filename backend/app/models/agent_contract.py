"""HTTP contract for agent endpoints (POST /agent/respond).

OpenAI-compatible chat message and tool-call shapes. Reuses :class:`ToolCall`
from :mod:`app.models.schemas` so transcripts and wire payloads share one model.
"""

from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.models.enums import TurnRole
from app.models.schemas import ToolCall


class AgentRequestMetadata(BaseModel):
    test_case_id: str | None = Field(
        default=None, description="Test case identifier from the eval platform"
    )
    turn_index: int | None = Field(
        default=None, description="Zero-based turn index in the test case conversation"
    )


class ChatMessage(BaseModel):
    role: TurnRole = Field(description="Message role: system, user, assistant, or tool")
    content: str | None = Field(
        default=None, description="Text content; null when only tool_calls are sent"
    )
    tool_calls: list[ToolCall] | None = Field(
        default=None, description="Assistant tool calls (OpenAI shape)"
    )
    tool_call_id: str | None = Field(
        default=None,
        description="For role=tool, id of the tool call this message responds to",
    )
    name: str | None = Field(
        default=None,
        description="Optional tool name for role=tool (OpenAI convention)",
    )


class AgentRequest(BaseModel):
    messages: list[ChatMessage] = Field(
        description="Full conversation history in OpenAI chat order"
    )
    metadata: AgentRequestMetadata | None = Field(
        default=None, description="Platform context for logging and evaluation"
    )


class TokenUsage(BaseModel):
    prompt_tokens: int | None = Field(
        default=None, description="Tokens in the prompt context"
    )
    completion_tokens: int | None = Field(
        default=None, description="Tokens in the completion"
    )
    total_tokens: int | None = Field(
        default=None, description="Total tokens if reported by the agent"
    )


class AgentResponse(BaseModel):
    messages: list[ChatMessage] = Field(
        description=(
            "All messages produced in this agent turn: assistant (with optional "
            "tool_calls), tool results, and final assistant reply"
        )
    )
    model: str | None = Field(
        default=None, description="Model identifier used for generation (e.g. gpt-4o)"
    )
    provider: str | None = Field(
        default=None,
        description="Provider identifier (e.g. openai, anthropic)",
    )
    usage: TokenUsage | None = Field(
        default=None, description="Optional aggregate token usage for cost tracking"
    )
    metadata: dict[str, object] | None = Field(
        default=None,
        description="Optional agent-defined metadata echoed for observability",
    )

    @model_validator(mode="after")
    def _last_message_must_be_assistant(self) -> Self:
        if self.messages and self.messages[-1].role != TurnRole.ASSISTANT:
            raise ValueError(
                "AgentResponse.messages must end with an assistant message"
            )
        return self
