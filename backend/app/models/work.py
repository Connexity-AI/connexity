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


class WorkDonePublic(BaseModel):
    title: str = Field(description="What was done, with its result")
    by: str = Field(description="A person, their assistant, or Connexity")
    at: datetime


class WorkSessionPublic(BaseModel):
    person: str
    assistant: str
    session: str = ""
    task: str = Field(description="The title of the task it is working on")


class WorkPublic(BaseModel):
    in_progress: list[WorkTaskPublic] = Field(
        description="Tasks an assistant holds, and tasks waiting for the person"
    )
    to_do: list[WorkTaskPublic] = Field(description="Everything else, in order")
    done: list[WorkDonePublic] = Field(description="The last 7 days, newest first")
    sessions: list[WorkSessionPublic] = Field(description="Sessions working now")
    waiting: int = Field(description="Tasks waiting for the person")


class WorkCountsPublic(BaseModel):
    waiting: int = Field(description="Tasks waiting for the person")
