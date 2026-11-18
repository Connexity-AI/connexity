"""What the Work page and `list_tasks` answer (plan `plans/2026-11-16-work-page.md`):
the workspace's tasks in Connexity's order, who is working on what, and what was done.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import TaskKind

TaskState = Literal["in_progress", "waiting", "to_do"]


class WorkHolderPublic(BaseModel):
    """Who holds a task: the person, their assistant and its session."""

    person: str
    assistant: str
    session: str = Field(default="", description="Empty when the session has no name")
    taken_at: datetime
    quiet_since: datetime | None = Field(
        default=None,
        description="When its session last asked for its next task, once that is "
        "more than 30 minutes ago; the task stays with the session",
    )


class WorkTaskRefPublic(BaseModel):
    key: str
    title: str
    state: TaskState
    waiting_for_person: bool = False


class WorkTaskPublic(BaseModel):
    key: str
    kind: TaskKind
    title: str = Field(description="The task in one plain sentence")
    line: str = Field(description="The type word, then the details")
    severity: str | None = Field(
        default=None, description="critical or warning, for an issue fix"
    )
    position: int = Field(description="Its place in the list, 1 at the top")
    state: TaskState
    waiting_for_person: bool = Field(
        default=False, description="The next move is the person's"
    )
    agent_id: uuid.UUID | None = None
    agent_name: str | None = None
    issue_id: uuid.UUID | None = None
    holder: WorkHolderPublic | None = None
    blocks: list[WorkTaskRefPublic] = Field(default_factory=list)
    blocked_by: list[WorkTaskRefPublic] = Field(default_factory=list)


class WorkDoneLinkPublic(BaseModel):
    """Where a finished task's work is: an agent's tab, or an issue."""

    kind: Literal["agent_spec", "agent_tests", "agent_calls", "issue"]
    id: uuid.UUID


class WorkDonePublic(BaseModel):
    title: str = Field(description="What was done, with its result")
    by: str = Field(description="A person, their assistant, or Connexity")
    at: datetime
    link: WorkDoneLinkPublic | None = None


class WorkSessionPublic(BaseModel):
    person: str
    assistant: str
    session: str = ""
    task: str = Field(description="The title of the task it is working on")


class WorkPublic(BaseModel):
    in_progress: list[WorkTaskPublic] = Field(
        description="Tasks an assistant holds, and questions waiting for the person"
    )
    to_do: list[WorkTaskPublic] = Field(description="Everything else, in order")
    done: list[WorkDonePublic] = Field(description="The last 7 days, newest first")
    sessions: list[WorkSessionPublic] = Field(description="Sessions working now")
    waiting: int = Field(description="Questions waiting for the person")
    assistant_connected: bool = Field(
        default=False, description="An assistant of the workspace is connected"
    )
    mcp_url: str | None = Field(
        default=None, description="The MCP address assistants connect to"
    )


class WorkMoveIn(BaseModel):
    key: str = Field(
        max_length=128,
        description="The task to move: one in To do, or one you hold, which goes back "
        "to To do",
    )
    before: str | None = Field(
        default=None,
        max_length=128,
        description="The To do task it now sits before; none for the end",
    )


class WorkCountsPublic(BaseModel):
    waiting: int = Field(description="Questions waiting for the person")
