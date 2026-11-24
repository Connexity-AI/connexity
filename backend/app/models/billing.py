"""Billing: the agency's subscription and what Billing shows of the card and details.

Card and billing details are read from Stripe when Billing opens and never stored.
"""

import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, Numeric, UniqueConstraint, text
from sqlmodel import Field, SQLModel

from app.models.agency import SubscriptionState
from app.models.columns import enum_type

# One subscription for every agency (Decided by Dmytro, 2026-11-23).
SUBSCRIPTION_PRICE_USD = 299
SUBSCRIPTION_INCLUDED_USD = 299

# The first scan a new agency gets without paying (Decided by Dmytro, 2026-11-24): the
# last 30 days, the latest 100 calls per agent, at most 500 calls per agency, and one
# included scan per voice platform account.
FIRST_SCAN_CALLS_PER_AGENT = 100
FIRST_SCAN_CALLS_PER_AGENCY = 500


class AgencyState(str, enum.Enum):
    """What an agency may do, from its subscription and what it has left
    (`docs-internal/billing.md`)."""

    # No subscription yet and the first scan is not finished: only the scan runs.
    first_scan = "first_scan"
    # No subscription and the first scan is done: paused.
    needs_subscription = "needs_subscription"
    active = "active"
    # Running, with less than about a week left at the current rate.
    low = "low"
    # The included amount and the balance are both used up: paused.
    out = "out"
    # The subscription is unpaid: paused.
    unpaid = "unpaid"


# New calls are recorded and checked, and tests may start.
RUNNING = frozenset({AgencyState.active, AgencyState.low})
# The first scan may read calls.
SCANNING = RUNNING | {AgencyState.first_scan}


class BalanceKind(str, enum.Enum):
    # Added by Connexity by hand. Top-ups add their own kind with their row.
    added = "added"
    # What one period's usage beyond the included amount drew. Negative.
    usage = "usage"


class BalanceEntry(SQLModel, table=True):
    """One line of an agency's prepaid balance. The balance is the sum of its lines."""

    __tablename__ = "balance_entry"
    __table_args__ = (
        UniqueConstraint(
            "agency_id", "kind", "period_start", name="uq_balance_entry_period"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agency_id: uuid.UUID = Field(
        foreign_key="agency.id", index=True, ondelete="CASCADE"
    )
    kind: BalanceKind = Field(sa_type=enum_type(BalanceKind))
    amount_usd: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    # For `usage`: the subscription period whose usage this line is. One per period.
    period_start: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    note: str | None = Field(default=None, max_length=255)
    created_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class BillingPause(SQLModel, table=True):
    """A stretch during which an agency was paused, and why. Calls made in it were not
    recorded and are never brought in afterwards."""

    __tablename__ = "billing_pause"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agency_id: uuid.UUID = Field(
        foreign_key="agency.id", index=True, ondelete="CASCADE"
    )
    reason: AgencyState = Field(sa_type=enum_type(AgencyState))
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    ended_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )


class IncludedScan(SQLModel, table=True):
    """The agency whose included first scan a voice platform account was used for.
    Another agency connecting the same account gets no included scan."""

    __tablename__ = "included_scan"

    key_fingerprint: str = Field(primary_key=True, max_length=64)
    agency_id: uuid.UUID = Field(foreign_key="agency.id", ondelete="CASCADE")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class FirstScanPublic(SQLModel):
    checked: int = Field(description="Calls the included first scan read")
    of: int = Field(
        description="Calls the last 30 days held; more than `checked` "
        "when the limit was reached"
    )


class MoneyPublic(SQLModel):
    """What an agency has left, in dollars."""

    state: AgencyState
    included_usd: float = Field(description="Included in the current period")
    included_left_usd: float
    balance_usd: float = Field(
        description="Prepaid balance, used after the included amount. Never negative"
    )
    period_end: datetime | None = Field(
        description="When the included amount is restored"
    )
    days_left: int | None = Field(
        description="About how many days what is left lasts at the rate of the last "
        "7 days; absent with too little usage to tell"
    )
    subscription_ended: bool = Field(
        default=False,
        description="In `needs_subscription`: a subscription existed and ended, "
        "rather than never having started",
    )
    first_scan: FirstScanPublic | None = Field(
        description="The included first scan, for an agency with no subscription"
    )


class StripeEvent(SQLModel, table=True):
    """A message from Stripe that was handled, by its id, so a repeat does nothing."""

    __tablename__ = "stripe_event"

    id: str = Field(primary_key=True, max_length=255)
    kind: str = Field(max_length=128)
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class SubscriptionPublic(SQLModel):
    state: SubscriptionState = Field(
        description="none, active, past_due (a renewal failed and is being retried; "
        "Connexity keeps working), unpaid or ended"
    )
    price_usd: int = Field(description="Dollars a month")
    included_usd: int = Field(description="Dollars of usage included each month")
    period_end: datetime | None = Field(
        description="When it renews, or ends if `ends_at_period_end`"
    )
    ends_at_period_end: bool = Field(
        description="Cancelled: it runs to `period_end` and is not renewed"
    )


class CardPublic(SQLModel):
    brand: str
    last4: str
    exp_month: int
    exp_year: int


class BillingDetailsPublic(SQLModel):
    name: str | None
    address: list[str] = Field(description="The address, one line per item")
    tax_ids: list[str]


class BillingPublic(SQLModel):
    subscription: SubscriptionPublic
    card: CardPublic | None
    details: BillingDetailsPublic | None
    read_from_stripe: bool = Field(
        description="False when Stripe could not be reached: the subscription is the "
        "last known one and the card and details are missing"
    )


class BillingLink(SQLModel):
    url: str = Field(description="A page on Stripe to send the person to")
