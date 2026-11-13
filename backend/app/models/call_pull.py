"""State of the scheduled call pull (`app/services/call_pull.py`). Not tenant-owned:
it belongs to a provider account (a key), which several workspaces may share."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, text
from sqlmodel import Field, SQLModel


class CallPullAccount(SQLModel, table=True):
    """Where the pull of one Retell account has got to."""

    __tablename__ = "call_pull_account"

    key_fingerprint: str = Field(primary_key=True, max_length=64)
    # Start time of the newest call the pull has dealt with.
    cursor: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore[call-overload]
    last_pulled_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    # After a 429 or a failure, no pull before this.
    paused_until: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    failures: int = Field(default=0)
    last_error: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class CallPullLease(SQLModel, table=True):
    """One row: the run that holds it until `held_until`. Runs never overlap."""

    __tablename__ = "call_pull_lease"

    id: int = Field(default=1, primary_key=True)
    held_until: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore[call-overload]
    holder: str = Field(max_length=64)
