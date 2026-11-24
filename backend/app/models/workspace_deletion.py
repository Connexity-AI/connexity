"""The record of a deleted workspace.

It belongs to the agency, not the workspace, so it outlives the workspace's data, and it
holds no call content: who deleted which workspace, when, and how much was removed.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, text
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type


class DeletionState(str, enum.Enum):
    deleting = "deleting"
    done = "done"
    # A step broke. "Try again" continues; what was already removed stays removed.
    failed = "failed"


class WorkspaceDeletion(SQLModel, table=True):
    __tablename__ = "workspace_deletion"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agency_id: uuid.UUID = Field(
        foreign_key="agency.id", index=True, ondelete="CASCADE"
    )
    # The workspace's row stays, with its name only (`company.deleted_at`).
    company_id: uuid.UUID = Field(foreign_key="company.id", unique=True)
    workspace_name: str = Field(max_length=255)
    deleted_by_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    # Kept as text so the record still names the person after their account is gone.
    deleted_by_name: str = Field(max_length=255)
    state: DeletionState = Field(
        default=DeletionState.deleting, sa_type=enum_type(DeletionState)
    )
    # What the workspace held when the deletion was asked for.
    calls: int = 0
    agents: int = 0
    issues: int = 0
    # The step and kind of error of a failed run. Never data from the workspace.
    error: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )


class WorkspaceDeletionPublic(SQLModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_name: str
    deleted_by: str = Field(description="The name of the person who deleted it")
    state: DeletionState
    calls: int
    agents: int
    issues: int
    created_at: datetime
    finished_at: datetime | None


class WorkspaceDeletionPreview(SQLModel):
    """What deleting a workspace removes, for the dialog that confirms it."""

    workspace_id: uuid.UUID
    workspace_name: str
    calls: int = Field(
        description="Calls, with their recordings' links and transcripts"
    )
    agents: int = Field(description="Agents, with their specs, scenarios and test runs")
    issues: int
    connections: list[str] = Field(
        description="The connected platforms whose stored keys are removed"
    )
    is_last: bool = Field(
        description="The agency's only workspace. It can be deleted; the agency then "
        "has none, and its subscription keeps running until it is cancelled"
    )


class AgencyWorkspaceRow(SQLModel):
    id: uuid.UUID
    name: str
    agents: int
    calls: int = Field(description="Calls stored")
    created_at: datetime
    state: DeletionState | None = Field(
        description="Set while a deletion is running or after it failed"
    )


class AgencyWorkspacesTable(SQLModel):
    workspaces: list[AgencyWorkspaceRow]
    can_delete: bool = Field(
        description="Whether the person is an Admin who can approve"
    )
    deleted: list[WorkspaceDeletionPublic] = Field(
        description="The agency's record of deleted workspaces, newest first"
    )


class WorkspaceDeleteRequest(SQLModel):
    name: str = Field(
        max_length=255, description="The workspace's name, typed to confirm"
    )
