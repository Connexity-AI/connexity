"""What the backend's `/mcp` routes answer: the standard shape every MCP tool returns.

Every answer carries the facts (`data`), the rules that apply to them, numbered next
steps naming the tool to call, and a link to the guide for this part of Connexity.
Lists add `next_cursor`. Errors carry a message, next steps and a guide in the same way
(see `McpErrorDetail`).
"""

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.models.enums import Platform

T = TypeVar("T")

GUIDE_GETTING_STARTED = "connexity://guides/getting-started"
GUIDE_WORKSPACES = "connexity://guides/workspaces"


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
    platform_agent_name: str | None = None
    created_at: datetime
