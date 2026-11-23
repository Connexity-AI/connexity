"""An agency: the thin account above its client workspaces.

It owns the people (and, later, the billing). A workspace belongs to exactly one
agency; a person can be in several. `agency_member` says what a person is in an agency;
`workspace_member` stays the table every access check reads, and is kept in step with
it by `app/crud/agency.py`. Plan: `plans/2026-11-23-agency-account.md`.
"""

import enum
import uuid
from datetime import UTC, datetime, timedelta

from pydantic import EmailStr
from sqlalchemy import Column, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.user import PASSWORD_MIN_LENGTH

# An invite works this long after it was last sent (design: "expires in 7 days").
INVITE_LIFETIME = timedelta(days=7)


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


class AgencyInvite(SQLModel, table=True):
    """An invitation to join an agency, sent to one email address.

    It carries what the person will be in the agency. Only a hash of the link's token is
    stored. An invite is open until it is accepted, cancelled (or declined), or seven
    days have passed since it was last sent.
    """

    __tablename__ = "agency_invite"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agency_id: uuid.UUID = Field(
        foreign_key="agency.id", index=True, ondelete="CASCADE"
    )
    # Lower-cased; joining needs an account with this address.
    email: str = Field(max_length=255, index=True)
    role: AgencyRole = Field(default=AgencyRole.member, sa_type=enum_type(AgencyRole))
    all_workspaces: bool = Field(
        default=True, sa_column_kwargs={"server_default": text("true")}
    )
    # The chosen workspaces' ids, when all_workspaces is off.
    workspace_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(
            "workspace_ids", JSONB, nullable=False, server_default=text("'[]'::jsonb")
        ),
    )
    can_approve: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("false")}
    )
    invited_by_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    token_hash: str = Field(max_length=64, unique=True, index=True)
    sent_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    accepted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    cancelled_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
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
    assistants: int = Field(
        description="How many assistants the person has connected; they reach what "
        "the person reaches"
    )


class AgencyInvitePublic(SQLModel):
    id: uuid.UUID
    email: EmailStr
    role: AgencyRole
    all_workspaces: bool
    workspace_ids: list[uuid.UUID]
    can_approve: bool
    expires_at: datetime
    invited_by: str | None = Field(
        description="The name of the person who invited them"
    )


class AgencyDetail(AgencyPublic):
    workspaces: list[AgencyWorkspace]
    members: list[AgencyMemberPublic]
    invites: list[AgencyInvitePublic] = Field(
        description="Invites still waiting; shown to Admins only"
    )


class AgencyInviteCreate(SQLModel):
    emails: list[str] = Field(min_length=1, max_length=50)
    role: AgencyRole = AgencyRole.member
    all_workspaces: bool = True
    workspace_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="The chosen workspaces, when all_workspaces is off; at least one",
    )
    can_approve: bool = False


class AgencyInviteRefusal(SQLModel):
    email: str
    reason: str = Field(description="invalid, member or invited")
    message: str


class AgencyInviteResult(SQLModel):
    sent: list[AgencyInvitePublic]
    refused: list[AgencyInviteRefusal]


class InviteLook(SQLModel):
    """What an invite link is, for the page that accepts it."""

    agency_name: str
    invited_by: str | None
    email: EmailStr
    workspaces: int = Field(description="How many workspaces the person will reach")
    has_account: bool = Field(description="Whether an account with this email exists")


class InviteSignUp(SQLModel):
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=40)


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


class InviteSignIn(SQLModel):
    password: str = Field(min_length=1, max_length=128)
