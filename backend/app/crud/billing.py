"""The agency's subscription as stored, and Stripe's handled messages."""

import uuid

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, select

from app.models.agency import Agency, SubscriptionState
from app.models.billing import (
    SUBSCRIPTION_INCLUDED_USD,
    SUBSCRIPTION_PRICE_USD,
    StripeEvent,
    SubscriptionPublic,
)
from app.services.stripe import Subscription


def subscription_public(agency: Agency) -> SubscriptionPublic:
    return SubscriptionPublic(
        state=agency.subscription_state,
        price_usd=SUBSCRIPTION_PRICE_USD,
        included_usd=SUBSCRIPTION_INCLUDED_USD,
        period_end=agency.subscription_period_end,
        ends_at_period_end=agency.subscription_ends_at_period_end,
    )


def set_customer(*, session: Session, agency: Agency, customer_id: str) -> Agency:
    agency.stripe_customer_id = customer_id
    session.add(agency)
    session.commit()
    session.refresh(agency)
    return agency


def store_subscription(
    *, session: Session, agency: Agency, subscription: Subscription | None
) -> Agency:
    """Make the agency's subscription what Stripe says it is now. Commits."""
    # Before the period moves on, the ledger's line for the old one is brought up to
    # date, so usage recorded since it was last settled is not lost.
    from app.services.billing_state import settle_period

    if (
        subscription is None
        or subscription.period_start != agency.subscription_period_start
    ):
        settle_period(session=session, agency=agency)
    if subscription is None:
        agency.stripe_subscription_id = None
        agency.subscription_state = SubscriptionState.none
        agency.subscription_period_start = None
        agency.subscription_period_end = None
        agency.subscription_ends_at_period_end = False
    else:
        agency.stripe_subscription_id = subscription.id
        agency.subscription_state = subscription.state
        agency.subscription_period_start = subscription.period_start
        agency.subscription_period_end = subscription.period_end
        agency.subscription_ends_at_period_end = (
            subscription.ends_at_period_end
            and subscription.state is not SubscriptionState.ended
        )
    session.add(agency)
    session.commit()
    session.refresh(agency)
    return agency


def agency_of_customer(*, session: Session, customer_id: str) -> Agency | None:
    return session.exec(
        select(Agency).where(Agency.stripe_customer_id == customer_id)
    ).first()


def agency_by_id(*, session: Session, agency_id: uuid.UUID) -> Agency | None:
    return session.get(Agency, agency_id)


def event_was_handled(*, session: Session, event_id: str) -> bool:
    return session.get(StripeEvent, event_id) is not None


def mark_event_handled(*, session: Session, event_id: str, kind: str) -> None:
    """Remember a handled message. Safe when two copies arrive at once. Commits."""
    session.execute(
        pg_insert(StripeEvent.__table__)  # type: ignore[attr-defined]
        .values(id=event_id, kind=kind[:128])
        .on_conflict_do_nothing()
    )
    session.commit()
