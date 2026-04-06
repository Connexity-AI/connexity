import uuid

from pydantic import BaseModel, Field

from app.models.test_case import TestCasePublic


class ToolDefinition(BaseModel):
    """A single tool/function definition the agent has access to."""

    name: str
    description: str
    parameters: dict[str, object] | None = None


class GenerateRequest(BaseModel):
    """Input for test case generation."""

    agent_prompt: str
    tools: list[ToolDefinition] = []
    count: int = Field(default=10, ge=1, le=50)
    focus_tags: list[str] = []
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    persist: bool = True
    agent_id: uuid.UUID | None = Field(
        default=None,
        description="When persist=true, bind created test cases to this agent",
    )


class GenerateResult(BaseModel):
    """Output from test case generation."""

    test_cases: list[TestCasePublic]
    count: int
    model_used: str
    generation_time_ms: int
