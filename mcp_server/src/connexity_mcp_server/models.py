from __future__ import annotations

from pydantic import BaseModel, Field


class AgentSummary(BaseModel):
    id: str
    name: str | None = None
    description: str | None = None
    mode: str | None = None
    platform: str | None = None
    has_draft: bool = False
    latest_published_version: int | None = None


class ListAgentsResult(BaseModel):
    agents: list[AgentSummary] = Field(default_factory=list)
    count: int = 0


class FindAgentsResult(BaseModel):
    query: str
    agents: list[AgentSummary] = Field(default_factory=list)
    count: int = 0
    message: str | None = None


class AgentDraftResult(BaseModel):
    agent_id: str
    version_id: str | None = None
    version: int | None = None
    system_prompt: str | None = None
    agent_model: str | None = None
    agent_provider: str | None = None
    agent_temperature: float | None = None
    tools: list[dict] = Field(default_factory=list)
    tools_count: int = 0


class UpdateAgentPromptResult(BaseModel):
    agent_id: str
    version_id: str | None = None
    version: int | None = None
    system_prompt: str | None = None
    updated: bool = True
