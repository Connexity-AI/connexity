"""Billing: the agency's subscription and what Billing shows of the card and details.

Card and billing details are read from Stripe when Billing opens and never stored.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, text
from sqlmodel import Field, SQLModel

from app.models.agency import SubscriptionState

# One subscription for every agency (Decided by Dmytro, 2026-11-23).
SUBSCRIPTION_PRICE_USD = 299
SUBSCRIPTION_INCLUDED_USD = 299


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
