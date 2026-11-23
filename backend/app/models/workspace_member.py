import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, text
from sqlmodel import Field, SQLModel


class WorkspaceMember(SQLModel, table=True):
    """A person's membership of a workspace (a company).

    A person can belong to several workspaces, one per client. Access to a workspace,
    on the web and through MCP, is decided by this table (`app/crud/workspace.py`).
    Its rows are kept in step with the person's place in the workspace's agency
    (`app/crud/agency.py`): every workspace of the agency for a person with "all
    workspaces", the chosen ones otherwise.
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
    agency_id: uuid.UUID
    agency_name: str


class WorkspaceCreate(SQLModel):
    name: str = Field(min_length=1, max_length=255)
    agency_id: uuid.UUID | None = Field(
        default=None,
        description="The agency to create the workspace in. Needed only when the "
        "person is an Admin of more than one agency.",
    )
