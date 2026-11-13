from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Answer(BaseModel, Generic[T]):
    """The standard answer of every Connexity tool."""

    data: T = Field(description="The facts: the result of the call")
    rules: list[str] = Field(
        default_factory=list,
        description="The rules that apply to what was returned. Follow them.",
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="What you can do next, in order, naming the tool to call",
    )
    guide: str = Field(description="URI of the guide for this part of Connexity")
    next_cursor: str | None = Field(
        default=None,
        description="On lists: pass as `cursor` for the next page; empty on the last",
    )


class Workspace(BaseModel):
    id: str
    name: str


class Agent(BaseModel):
    id: str
    name: str
    platform: str | None = None
    platform_agent_id: str | None = None
    platform_agent_name: str | None = None
    created_at: datetime


class ReadinessStep(BaseModel):
    key: str
    name: str
    state: str = Field(description="done, in_progress or not_started")
    detail: str | None = None


class Readiness(BaseModel):
    steps: list[ReadinessStep]
    done: int
    total: int
    percent: int
    first_scan_done: bool
    mcp_url: str | None = None


class Connection(BaseModel):
    platform: str
    masked_api_key: str
    replaced_earlier_key: bool
    connected_by: str | None = None


class AgentToAdd(BaseModel):
    platform_agent_id: str = Field(description="The agent's id in Retell")
    name: str | None = Field(
        default=None, description="Defaults to the agent's name in Retell"
    )


class RefusedAgent(BaseModel):
    platform_agent_id: str
    reason: str


class AddedAgents(BaseModel):
    added: list[Agent] = Field(default_factory=list)
    already_added: list[Agent] = Field(default_factory=list)
    refused: list[RefusedAgent] = Field(default_factory=list)


class AgentScan(BaseModel):
    agent_id: str
    name: str
    stored: int
    total: int | None = None
    finished: bool


class ScanProgress(BaseModel):
    agents: list[AgentScan] = Field(default_factory=list)
    stored_this_step: int
    finished: bool
    calls_without_versions: int = 0


class WorstFinding(BaseModel):
    title: str
    key: str | None = None
    category: str
    severity: str
    found_by: str


class CallItem(BaseModel):
    id: str
    started_at: str
    agent_id: str
    agent_name: str
    caller_last_four: str | None = None
    duration_seconds: int | None = None
    result: str
    worst_finding: WorstFinding | None = None


class CallTiles(BaseModel):
    calls: int
    failed: int
    degraded: int
    clean: int
    unchecked: int


class Calls(BaseModel):
    tiles: CallTiles
    calls: list[CallItem] = Field(default_factory=list)


class Issue(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    type: str
    title: str
    category: str
    severity: str
    found_by: str
    state: str
    calls_affected: int
    calls_total: int
    first_seen_at: str | None = None
    last_seen_at: str | None = None


class Category(BaseModel):
    key: str
    name: str
    position: int
    kind: str


ListWorkspacesResult = Answer[list[Workspace]]
AddAgentsResult = Answer[AddedAgents]
ConnectVoicePlatformResult = Answer[Connection]
GetReadinessResult = Answer[Readiness]
CreateWorkspaceResult = Answer[Workspace]
ListAgentsResult = Answer[list[Agent]]
ScanCallsResult = Answer[ScanProgress]
ListCategoriesResult = Answer[list[Category]]
ListIssuesResult = Answer[list[Issue]]
ListCallsResult = Answer[Calls]
