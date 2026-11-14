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

from app.models.call_list import CallListItemPublic, CallTilesPublic
from app.models.enums import Platform, SpecRuleTouches
from app.models.issue_list import IssueListItemPublic, IssueTilesPublic
from app.models.spec import SpecState

T = TypeVar("T")

GUIDE_GETTING_STARTED = "connexity://guides/getting-started"
GUIDE_WORKSPACES = "connexity://guides/workspaces"
GUIDE_READINESS = "connexity://guides/readiness"
GUIDE_CONNECT = "connexity://guides/connect"
GUIDE_CATEGORIES = "connexity://guides/categories"
GUIDE_ISSUES = "connexity://guides/issues"
GUIDE_SPEC = "connexity://guides/spec"
GUIDE_CALLS = "connexity://guides/calls"


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
    spec: SpecState | None = Field(
        default=None,
        description="none, current, or needs_review (adopted, or behind the agent)",
    )
    spec_version: int | None = Field(
        default=None, description="Its latest spec version"
    )


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


class McpSpecRule(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
    category: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=64)
    ] = Field(description="A category key from `list_categories`")
    quote: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=4000)
    ] = Field(default=None, description="The prompt's words the rule rests on")
    touches: SpecRuleTouches | None = Field(
        default=None, description="money, safety or compliance, when it protects one"
    )
    key: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=64)
    ] = Field(
        default=None, description="Only for a rule kept from the previous version"
    )


class McpWriteSpec(BaseModel):
    rules: list[McpSpecRule] = Field(max_length=1000)


class McpArchiveIssue(BaseModel):
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ] = Field(description="Why, in the person's own words")
    duration: Literal["until_spike", "forever"] = "until_spike"


class McpUnarchiveIssue(BaseModel):
    reason: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=2000)
    ] = None


class McpIssues(BaseModel):
    tiles: IssueTilesPublic = Field(description="Counts for the agent and period")
    issues: list[IssueListItemPublic] = Field(description="Worst first")


class McpCalls(BaseModel):
    tiles: CallTilesPublic = Field(description="Counts for the filters and period")
    calls: list[CallListItemPublic]
