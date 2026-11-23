"""Requests to reset a password, and the single-use links they produce.

One row per request, whether or not the email has an account: the rows are also what
the limits count. Nothing a person typed is stored in the clear: the email and the
network address are hashed, and so is the link's token. A person is not owned by one
workspace, so there is no `company_id`. Plan: `plans/2026-11-23-password-reset.md`.
"""

import uuid
from datetime import UTC, datetime, timedelta

from pydantic import EmailStr
from sqlalchemy import DateTime, text
from sqlmodel import Field, SQLModel

from app.models.user import PASSWORD_MIN_LENGTH

# How long a link works, and what the screens and the email say ("expires in 1 hour").
RESET_LINK_LIFETIME = timedelta(hours=1)
# "Send again" is offered this long after a send; the backend refuses sooner ones.
RESET_RESEND_AFTER = timedelta(seconds=45)
# Decided by Dmytro, 2026-11-23.
RESET_LIMIT_WINDOW = timedelta(hours=1)
RESET_LIMIT_PER_EMAIL = 3
RESET_LIMIT_PER_ADDRESS = 10


class PasswordResetRequest(SQLModel, table=True):
    __tablename__ = "password_reset_request"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # SHA-256 of the lower-cased email asked for, and of the caller's network address.
    email_hash: str = Field(max_length=64, index=True)
    address_hash: str = Field(max_length=64, index=True)
    # Empty when the email has no account that can reset a password.
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True, ondelete="CASCADE"
    )
    # SHA-256 of the link's token; the token itself is only ever in the email.
    token_hash: str | None = Field(default=None, max_length=64, unique=True, index=True)
    expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    # Set when the link set a password, or when a newer link replaced it.
    used_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class PasswordResetAsk(SQLModel):
    email: EmailStr = Field(max_length=255)


class PasswordResetLink(SQLModel):
    """What the "Set a new password" page shows for a link that still works."""

    email: EmailStr


class PasswordResetNew(SQLModel):
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=40)
