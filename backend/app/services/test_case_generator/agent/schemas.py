"""Request/response models for the test-case AI agent (POST /test-cases/ai)."""

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.models import ConversationTurn, TestCasePublic


class AgentMode(StrEnum):
    CREATE = "create"
    FROM_TRANSCRIPT = "from_transcript"
    EDIT = "edit"


class TestCaseAgentRequest(BaseModel):
    """Input for the single-turn test-case AI agent."""

    mode: AgentMode
    user_message: str = Field(min_length=1)
    agent_id: uuid.UUID
    agent_version: int | None = Field(
        default=None,
        ge=1,
        description="Agent version to load prompt/tools from; defaults to agent's current version",
    )
    transcript: list[ConversationTurn] | None = None
    test_case_id: uuid.UUID | None = Field(
        default=None,
        description="Required when mode=edit; must belong to agent_id",
    )
    persist: bool | None = Field(
        default=None,
        description="Default true for create/from_transcript; default false for edit",
    )
    model: str | None = None
    provider: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)

    @model_validator(mode="after")
    def _validate_mode_and_persist(self) -> "TestCaseAgentRequest":
        if not self.user_message.strip():
            msg = "user_message must not be empty"
            raise ValueError(msg)

        if self.mode == AgentMode.FROM_TRANSCRIPT:
            if not self.transcript:
                msg = "transcript is required when mode is from_transcript"
                raise ValueError(msg)
        elif self.transcript is not None:
            msg = "transcript is only allowed when mode is from_transcript"
            raise ValueError(msg)

        if self.mode == AgentMode.EDIT:
            if self.test_case_id is None:
                msg = "test_case_id is required when mode is edit"
                raise ValueError(msg)
        elif self.test_case_id is not None:
            msg = "test_case_id is only allowed when mode is edit"
            raise ValueError(msg)

        default_persist = self.mode != AgentMode.EDIT
        resolved = self.persist if self.persist is not None else default_persist
        return self.model_copy(update={"persist": resolved})


class TestCaseAgentResult(BaseModel):
    """Output from the test-case AI agent."""

    mode: AgentMode
    created: list[TestCasePublic] = Field(default_factory=list)
    edited: TestCasePublic | None = None
    model_used: str
    latency_ms: int
    token_usage: dict[str, int] | None = None
    cost_usd: float | None = None
