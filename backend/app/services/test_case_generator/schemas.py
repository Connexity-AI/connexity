import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.test_case import TestCasePublic


class ToolDefinition(BaseModel):
    """A single tool/function definition the agent has access to."""

    name: str
    description: str
    parameters: dict[str, object] | None = None


def tool_definitions_from_agent_tools(
    raw: list[dict[str, Any]] | None,
) -> list[ToolDefinition]:
    """Map OpenAI-style tool dicts (type/function) to ToolDefinition for prompts."""
    if not raw:
        return []
    out: list[ToolDefinition] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        fn = item.get("function")
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        desc = fn.get("description")
        params = fn.get("parameters")
        out.append(
            ToolDefinition(
                name=str(name or ""),
                description=str(desc or ""),
                parameters=params if isinstance(params, dict) else None,
            )
        )
    return out


class GenerateRequest(BaseModel):
    """Input for test case generation."""

    agent_prompt: str | None = Field(
        default=None,
        description="Agent system prompt; optional if agent_id is set (loaded from AgentVersion)",
    )
    tools: list[ToolDefinition] = Field(default_factory=list)
    count: int = Field(default=10, ge=1, le=200)
    focus_tags: list[str] = Field(default_factory=list)
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    persist: bool = True
    agent_id: uuid.UUID | None = Field(
        default=None,
        description="When set, may load prompt/tools from AgentVersion; when persist=true, bind test cases",
    )
    agent_version: int | None = Field(
        default=None,
        ge=1,
        description="Version to load config from when agent_id is set; defaults to agent's current version",
    )

    @model_validator(mode="after")
    def validate_prompt_or_agent(self) -> "GenerateRequest":
        has_usable_prompt = (
            self.agent_prompt is not None and self.agent_prompt.strip() != ""
        )
        if not has_usable_prompt and self.agent_id is None:
            msg = "Either agent_prompt or agent_id must be provided"
            raise ValueError(msg)
        if self.agent_version is not None and self.agent_id is None:
            msg = "agent_version requires agent_id"
            raise ValueError(msg)
        return self


class GenerateResult(BaseModel):
    """Output from test case generation."""

    test_cases: list[TestCasePublic]
    count: int
    model_used: str
    generation_time_ms: int
