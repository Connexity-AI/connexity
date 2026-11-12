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
    connect_command: str | None = None


class Connection(BaseModel):
    platform: str
    masked_api_key: str
    replaced_earlier_key: bool
    connected_by: str | None = None


ListWorkspacesResult = Answer[list[Workspace]]
ConnectVoicePlatformResult = Answer[Connection]
GetReadinessResult = Answer[Readiness]
CreateWorkspaceResult = Answer[Workspace]
ListAgentsResult = Answer[list[Agent]]
