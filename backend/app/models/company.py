import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, text
from sqlmodel import Field, SQLModel


def workspace_name_from_email(email: str) -> str:
    """A first name for a new workspace, from its first user's email domain.

    The domain's first part, each word capitalised: `ann@bright-dental.com` gives
    "Bright Dental" (design, 2026-11-12).
    """
    _, at, domain = email.rpartition("@")
    first = domain.strip().split(".")[0] if at else ""
    words = [w for w in re.split(r"[-_]", first) if w]
    name = " ".join(w[0].upper() + w[1:] for w in words)
    return name[:255] or "My workspace"


class Company(SQLModel, table=True):
    __tablename__ = "company"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )
    # A company is a workspace: one client of an agency (Decided 2026-11-12).
    name: str = Field(default="Workspace", max_length=255)
    # When every added agent's first scan had finished, the first time. Stays set when
    # agents are added later (their own scans still run).
    first_scan_done_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    # When onboarding was first complete (`services/onboarding_finish.py`). Stays set:
    # a question raised later does not reopen onboarding.
    onboarding_completed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
