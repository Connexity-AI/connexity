import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from pydantic import ConfigDict
from sqlalchemy import Column, Text, text
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import (
    PromptEditorSessionStatus,
    PromptEditStatus,
    TurnRole,
)
from app.models.run import Run

if TYPE_CHECKING:
    from app.models.agent import Agent


class PromptEditorSessionBase(SQLModel):
    model_config = ConfigDict(use_enum_values=True)

    title: str | None = Field(
        default=None,
        max_length=255,
        description="Session title (auto-generated or user-set)",
    )
    status: PromptEditorSessionStatus = Field(
        default=PromptEditorSessionStatus.ACTIVE,
        description="active or archived",
    )


class PromptEditorSession(PromptEditorSessionBase, table=True):
    __tablename__ = "prompt_editor_session"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(
        foreign_key="agent.id",
        index=True,
        description="Agent this prompt editor session belongs to",
    )
    created_by: uuid.UUID = Field(
        foreign_key="user.id",
        index=True,
        description="User who owns this session",
    )
    run_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="run.id",
        description="Optional eval run for context injection",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={
            "server_default": text("now()"),
            "onupdate": lambda: datetime.now(UTC),
        },
    )

    agent: "Agent" = Relationship(back_populates="prompt_editor_sessions")
    messages: list["PromptEditorMessage"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    run: Run | None = Relationship()


class PromptEditorSessionCreate(SQLModel):
    agent_id: uuid.UUID = Field(description="Agent to attach the session to")
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Optional title; auto-generated if omitted",
    )
    run_id: uuid.UUID | None = Field(
        default=None,
        description="Optional run for eval context",
    )


class PromptEditorSessionUpdate(SQLModel):
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Session title",
    )
    status: PromptEditorSessionStatus | None = Field(
        default=None,
        description="active or archived",
    )


class PromptEditorSessionPublic(PromptEditorSessionBase):
    id: uuid.UUID = Field(description="Session id")
    agent_id: uuid.UUID = Field(description="Agent id")
    created_by: uuid.UUID = Field(description="Owner user id")
    run_id: uuid.UUID | None = Field(description="Linked run id if any")
    created_at: datetime = Field(description="Created at")
    updated_at: datetime = Field(description="Updated at")
    message_count: int = Field(description="Number of messages in the session")


class PromptEditorSessionsPublic(SQLModel):
    data: list[PromptEditorSessionPublic] = Field(description="Sessions")
    count: int = Field(description="Total matching sessions")


class PromptEditorMessageBase(SQLModel):
    model_config = ConfigDict(use_enum_values=True)

    role: TurnRole = Field(description="Message role (user, assistant, …)")
    content: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Full message text",
    )


class PromptEditorMessage(PromptEditorMessageBase, table=True):
    __tablename__ = "prompt_editor_message"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(
        foreign_key="prompt_editor_session.id",
        index=True,
        description="Parent session",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )

    session: PromptEditorSession = Relationship(back_populates="messages")
    edits: list["PromptEdit"] = Relationship(
        back_populates="message",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class PromptEdit(SQLModel, table=True):
    __tablename__ = "prompt_edit"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    message_id: uuid.UUID = Field(
        foreign_key="prompt_editor_message.id",
        index=True,
    )
    start_line: int
    end_line: int
    new_content: str = Field(sa_column=Column(Text, nullable=False))
    original_content: str = Field(sa_column=Column(Text, nullable=False))
    status: PromptEditStatus = Field(default=PromptEditStatus.PENDING)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )

    message: PromptEditorMessage = Relationship(back_populates="edits")


class PromptEditCreate(SQLModel):
    start_line: int
    end_line: int
    new_content: str
    original_content: str


class PromptEditPublic(SQLModel):
    model_config = ConfigDict(use_enum_values=True)

    id: uuid.UUID
    message_id: uuid.UUID
    start_line: int
    end_line: int
    new_content: str
    original_content: str
    status: PromptEditStatus
    created_at: datetime


class PromptEditStatusUpdate(SQLModel):
    status: Literal["accepted", "declined"]


class PromptEditBatchStatusUpdate(SQLModel):
    status: Literal["accepted", "declined"]
    edit_ids: list[uuid.UUID] | None = None


class PromptEditorMessageCreate(SQLModel):
    session_id: uuid.UUID = Field(description="Session to append to")
    role: TurnRole = Field(description="Message role")
    content: str = Field(description="Message body")


class PromptEditorMessagePublic(PromptEditorMessageBase):
    id: uuid.UUID = Field(description="Message id")
    session_id: uuid.UUID = Field(description="Session id")
    created_at: datetime = Field(description="Created at")
    edits: list[PromptEditPublic] = Field(default_factory=list)


class PromptEditorMessagesPublic(SQLModel):
    data: list[PromptEditorMessagePublic] = Field(description="Messages")
    count: int = Field(description="Total messages in the query")
