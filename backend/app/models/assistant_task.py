"""The tasks assistants took (`plans/2026-11-15-next-task.md`).

Tasks are worked out from the workspace every time they are asked for
(`app/services/work.py`); a row only records that an assistant took one, and what
became of it. Rows are kept, never deleted.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Text, text
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import AssistantTaskState, TaskKind


def _now() -> datetime:
    return datetime.now(UTC)


class AssistantTask(SQLModel, table=True):
    __tablename__ = "assistant_task"
    __table_args__ = (
        # One assistant at a time on a task.
        Index(
            "ix_assistant_task_one_open",
            "company_id",
            "task_key",
            unique=True,
            postgresql_where=text("state = 'in_progress'"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    # The task's key, such as "spec:<agent id>" or "issue:<issue id>".
    task_key: str = Field(max_length=128)
    kind: TaskKind = Field(sa_type=enum_type(TaskKind))
    title: str = Field(sa_column=Column("title", Text, nullable=False))
    agent_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("agent.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    # Who took it: the person, and the assistant that acted for them.
    taken_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    taken_by_email: str = Field(max_length=255)
    assistant_name: str = Field(max_length=255)
    # The name the assistant gave this session ("Onboarding"); empty when it gave none.
    # Sessions are told apart by the person, the assistant and this name.
    session_name: str = Field(
        default="", max_length=40, sa_column_kwargs={"server_default": ""}
    )
    state: AssistantTaskState = Field(
        default=AssistantTaskState.IN_PROGRESS, sa_type=enum_type(AssistantTaskState)
    )
    taken_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )
    # When its session last asked for its next task: a task whose session has been
    # silent for `QUIET_MINUTES` shows as quiet (plan
    # `plans/2026-11-18-work-task-states.md`). None until the session asks again.
    last_seen_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    # When the assistant's part ended: done or returned.
    ended_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    # When it was done.
    done_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
