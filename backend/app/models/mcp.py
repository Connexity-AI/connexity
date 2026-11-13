"""What the backend's `/mcp` routes answer: the standard shape every MCP tool returns.

Every answer carries the facts (`data`), the rules that apply to them, numbered next
steps naming the tool to call, and a link to the guide for this part of Connexity.
Lists add `next_cursor`. Errors carry a message, next steps and a guide in the same way
(see `McpErrorDetail`).
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, StringConstraints

from app.models.enums import Platform

T = TypeVar("T")

GUIDE_GETTING_STARTED = "connexity://guides/getting-started"
GUIDE_WORKSPACES = "connexity://guides/workspaces"
GUIDE_READINESS = "connexity://guides/readiness"
GUIDE_CONNECT = "connexity://guides/connect"
GUIDE_CATEGORIES = "connexity://guides/categories"
GUIDE_ISSUES = "connexity://guides/issues"


class McpAnswer(BaseModel, Generic[T]):
    data: T = Field(description="The facts: the result of the call")
    rules: list[str] = Field(
        default_factory=list,
        description="The rules that apply to what was returned, one sentence each",
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="Steps the assistant can take next, in order, naming the tool",
    )
    guide: str = Field(description="The guide for this part of Connexity")
    next_cursor: str | None = Field(
        default=None,
        description="On lists: pass as `cursor` for the next page; empty on the last",
    )


class McpErrorDetail(BaseModel):
    """The `detail` of an error answered by an `/mcp` route."""

    error: str
    next_steps: list[str] = Field(default_factory=list)
    guide: str = GUIDE_GETTING_STARTED


class McpWorkspace(BaseModel):
    id: uuid.UUID
    name: str


class McpAgent(BaseModel):
    id: uuid.UUID
    name: str
    platform: Platform | None = None
    platform_agent_id: str | None = Field(
        default=None, description="The agent's id on its voice platform (Retell)"
    )
    platform_agent_name: str | None = None
    created_at: datetime


class McpVoicePlatform(StrEnum):
    RETELL = "retell"
    VAPI = "vapi"
    ELEVENLABS = "elevenlabs"


class McpConnectVoicePlatform(BaseModel):
    platform: McpVoicePlatform = McpVoicePlatform.RETELL
    api_key: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)
    ]


class McpConnection(BaseModel):
    platform: str
    masked_api_key: str
    replaced_earlier_key: bool
    connected_by: str | None = Field(
        default=None, description="The person, and the assistant, who connected it"
    )


class McpAgentToAdd(BaseModel):
    platform_agent_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    name: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=255)
    ] = Field(default=None, description="Defaults to the agent's name on the platform")


class McpAddAgents(BaseModel):
    agents: list[McpAgentToAdd] = Field(min_length=1, max_length=100)


class McpRefusedAgent(BaseModel):
    platform_agent_id: str
    reason: str


class McpAddedAgents(BaseModel):
    added: list[McpAgent]
    already_added: list[McpAgent]
    refused: list[McpRefusedAgent]


class McpAgentScan(BaseModel):
    agent_id: uuid.UUID
    name: str
    stored: int = Field(description="Calls stored from the agent's scan window")
    total: int | None = Field(
        description="Finished calls Retell listed in the window; empty until listed"
    )
    finished: bool


class McpScanProgress(BaseModel):
    agents: list[McpAgentScan]
    stored_this_step: int
    finished: bool = Field(description="Every added agent's first scan has finished")
    calls_without_versions: int = Field(
        description="Stored calls whose agent version could not be resolved"
    )


class McpIssue(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    type: str = Field(description="The check that finds it, e.g. booking_duplicated")
    title: str
    category: str
    severity: Literal["critical", "warning"]
    found_by: Literal["rule", "model"] = Field(
        description="rule: deterministic code over the call; model: a classifier or judge"
    )
    state: str
    calls_affected: int
    calls_total: int = Field(description="The agent's stored calls: 'in N of M calls'")
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
