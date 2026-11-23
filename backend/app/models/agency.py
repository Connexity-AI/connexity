"""An agency: the thin account above its client workspaces.

It owns the people (and, later, the billing). A workspace belongs to exactly one
agency; a person can be in several. `agency_member` says what a person is in an agency;
`workspace_member` stays the table every access check reads, and is kept in step with
it by `app/crud/agency.py`. Plan: `plans/2026-11-23-agency-account.md`.
"""

import enum
import uuid
from datetime import UTC, datetime

from pydantic import EmailStr
from sqlalchemy import DateTime, text
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type


class AgencyRole(str, enum.Enum):
    # Manages people and billing, and creates workspaces.
    admin = "admin"
    # Works in their workspaces.
    member = "member"


class Agency(SQLModel, table=True):
    __tablename__ = "agency"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class AgencyMember(SQLModel, table=True):
    """A person in an agency."""

    __tablename__ = "agency_member"

    agency_id: uuid.UUID = Field(
        foreign_key="agency.id", primary_key=True, ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id", primary_key=True, index=True, ondelete="CASCADE"
    )
    role: AgencyRole = Field(default=AgencyRole.member, sa_type=enum_type(AgencyRole))
    # Reaches every workspace of the agency, including ones created later. When off,
    # the person reaches the workspaces chosen for them.
    all_workspaces: bool = Field(
        default=True, sa_column_kwargs={"server_default": text("true")}
    )
    # May make the critical decisions in their workspaces. Stored and returned;
    # enforced with invites, the first moment a person without it can exist.
    can_approve: bool = Field(
        default=True, sa_column_kwargs={"server_default": text("true")}
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class AgencyPublic(SQLModel):
    """An agency as the signed-in person sees it."""

    id: uuid.UUID
    name: str
    role: AgencyRole = Field(description="The signed-in person's role in it")
    all_workspaces: bool
    can_approve: bool


class AgencyWorkspace(SQLModel):
    id: uuid.UUID
    name: str


class AgencyMemberPublic(SQLModel):
    user_id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: AgencyRole
    all_workspaces: bool
    workspace_ids: list[uuid.UUID] = Field(
        description="The workspaces the person reaches; every one of the agency's "
        "when all_workspaces is on"
    )
    can_approve: bool
    is_you: bool


class AgencyDetail(AgencyPublic):
    workspaces: list[AgencyWorkspace]
    members: list[AgencyMemberPublic]


class AgencyUpdate(SQLModel):
    name: str = Field(min_length=1, max_length=255)


class AgencyMemberUpdate(SQLModel):
    """Only the fields sent are changed."""

    role: AgencyRole | None = None
    all_workspaces: bool | None = None
    workspace_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="The chosen workspaces, when all_workspaces is off; replaces the "
        "person's earlier choice",
    )
    can_approve: bool | None = None
