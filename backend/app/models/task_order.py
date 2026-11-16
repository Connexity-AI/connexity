"""The person's order of the assistant's tasks (plan `plans/2026-11-16-reorder.md`).

One row per workspace: the To do tasks' keys as the person last left them. Connexity's
order fills in everything else (`app/services/work.py`, `apply_order`).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(UTC)


class TaskOrder(SQLModel, table=True):
    __tablename__ = "task_order"

    company_id: uuid.UUID = Field(foreign_key="company.id", primary_key=True)
    # Task keys, top first, as the person left To do after their last move.
    keys: list[str] = Field(
        default_factory=list, sa_column=Column("keys", JSONB, nullable=False)
    )
    # The last move: the task, who moved it (the person, and the assistant that acted
    # for them) and when.
    moved_key: str = Field(max_length=128)
    moved_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    moved_by_email: str = Field(max_length=255)
    assistant_name: str | None = Field(default=None, max_length=255)
    moved_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )
