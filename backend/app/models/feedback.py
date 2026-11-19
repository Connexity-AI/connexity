"""What assistants report about Connexity itself through MCP (`send_feedback`): bugs
and feature requests, stored per workspace and posted to the team's Notion database
(plan `plans/2026-11-19-assistant-feedback.md`)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import FeedbackKind


def _now() -> datetime:
    return datetime.now(UTC)


class FeedbackReport(SQLModel, table=True):
    __tablename__ = "feedback_report"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    kind: FeedbackKind = Field(sa_type=enum_type(FeedbackKind))
    title: str = Field(max_length=200)
    what_happened: str | None = Field(default=None, sa_column=Column(Text))
    wanted: str | None = Field(default=None, sa_column=Column(Text))
    tool: str | None = Field(default=None, max_length=100)
    error: str | None = Field(default=None, sa_column=Column(Text))
    ids: list[str] | None = Field(
        default=None, sa_column=Column("ids", JSONB, nullable=True)
    )
    # Who sent it: the person, and the assistant that acted for them.
    sent_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    assistant_name: str | None = Field(default=None, max_length=255)
    session_name: str | None = Field(default=None, max_length=40)
    connexity_version: str = Field(max_length=100)
    received_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )
    # Posting to Notion: its page once it got there; otherwise the tries so far and
    # why the last one failed.
    notion_page_id: str | None = Field(default=None, max_length=64)
    posted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    tries: int = Field(default=0, sa_column_kwargs={"server_default": "0"})
    # When a post started; another post skips the report until it is stale.
    claimed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    last_error: str | None = Field(default=None, max_length=500)
