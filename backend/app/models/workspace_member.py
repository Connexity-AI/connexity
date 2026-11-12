import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, text
from sqlmodel import Field, SQLModel


class WorkspaceMember(SQLModel, table=True):
    """A person's membership of a workspace (a company).

    A person can belong to several workspaces, one per client. Access to a workspace,
    on the web and through MCP, is decided by this table (`app/crud/workspace.py`).
    """

    __tablename__ = "workspace_member"

    user_id: uuid.UUID = Field(
        foreign_key="user.id", primary_key=True, ondelete="CASCADE"
    )
    company_id: uuid.UUID = Field(
        foreign_key="company.id", primary_key=True, index=True, ondelete="CASCADE"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class WorkspacePublic(SQLModel):
    id: uuid.UUID
    name: str
    is_open: bool


class WorkspaceCreate(SQLModel):
    name: str = Field(min_length=1, max_length=255)
