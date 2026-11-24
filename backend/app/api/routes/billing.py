"""Agency settings › Billing: the subscription, the card and billing details.

Only Admins. Paying, the card and the billing details happen on Stripe's pages; these
routes answer the links to them and what Stripe then knows. Without Stripe's settings
every route answers 404 and the web app shows no Billing section.
"""

import logging
import uuid

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.agencies import _mine
from app.core.config import settings
from app.crud import billing as crud_billing
from app.models import (
    BillingDetailsPublic,
    BillingLink,
    BillingPublic,
    CardPublic,
)
from app.models.agency import Agency, AgencyRole, SubscriptionState
from app.services import stripe
from app.services.stripe import StripeError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agencies", tags=["billing"])

STRIPE_DOWN = "The payment provider could not be reached. Try again in a minute."


def _as_billing_admin(
    session: SessionDep, user_id: uuid.UUID, agency_id: uuid.UUID
) -> Agency:
    if not settings.billing_enabled:
        raise HTTPException(status_code=404, detail="Billing is not set up")
    agency, membership = _mine(session, user_id, agency_id)
    if membership.role != AgencyRole.admin:
        asking = crud.admin_names(session=session, agency_id=agency.id)
        raise HTTPException(
            status_code=403, detail=f"Only Admins can see billing. Ask {asking}."
        )
    return agency


def _billing_page(done: bool = False) -> str:
    site = settings.public_site_url
    if not site:
        raise HTTPException(status_code=404, detail="Billing is not set up")
    return f"{site}/agency/?section=billing" + ("&checkout=done" if done else "")


async def sync_subscription(session: SessionDep, agency: Agency) -> Agency:
    """Read the agency's subscription from Stripe and store it.

    Raises:
        StripeError: Stripe could not be read; what is stored stays as it was.
    """
    if not agency.stripe_customer_id:
        return agency
    subscription = await stripe.current_subscription(
        customer_id=agency.stripe_customer_id
    )
    return crud_billing.store_subscription(
        session=session, agency=agency, subscription=subscription
    )


@router.get("/{agency_id}/billing", response_model=BillingPublic)
async def read_billing(
    session: SessionDep, current_user: CurrentUser, agency_id: uuid.UUID
) -> BillingPublic:
    """The subscription, read again from Stripe, with the card and billing details.
    When Stripe cannot be reached, the last known subscription without them."""
    agency = _as_billing_admin(session, current_user.id, agency_id)
    card = details = None
    fresh = True
    if agency.stripe_customer_id:
        try:
            agency = await sync_subscription(session, agency)
            found, about = await stripe.card_and_details(
                customer_id=agency.stripe_customer_id or "",
                subscription_id=agency.stripe_subscription_id,
            )
            card = CardPublic(**found.__dict__) if found else None
            details = BillingDetailsPublic(**about.__dict__)
        except StripeError as exc:
            logger.warning("Billing could not be read from Stripe: %s", exc)
            fresh = False
    return BillingPublic(
        subscription=crud_billing.subscription_public(agency),
        card=card,
        details=details,
        read_from_stripe=fresh,
    )


@router.post("/{agency_id}/billing/checkout", response_model=BillingLink)
async def start_subscription(
    session: SessionDep, current_user: CurrentUser, agency_id: uuid.UUID
) -> BillingLink:
    """Stripe's page that starts the subscription. Refused when one is running. Any
    earlier page that was opened and not paid stops working."""
    agency = _as_billing_admin(session, current_user.id, agency_id)
    try:
        if not agency.stripe_customer_id:
            customer_id = await stripe.create_customer(
                name=agency.name, agency_id=str(agency.id)
            )
            agency = crud_billing.set_customer(
                session=session, agency=agency, customer_id=customer_id
            )
        agency = await sync_subscription(session, agency)
        if agency.subscription_state in (
            SubscriptionState.active,
            SubscriptionState.past_due,
            SubscriptionState.unpaid,
        ):
            raise HTTPException(
                status_code=409, detail="This agency already has a subscription."
            )
        # An earlier page that was opened and never paid must not stay payable.
        await stripe.expire_open_checkouts(customer_id=agency.stripe_customer_id or "")
        url = await stripe.create_checkout(
            customer_id=agency.stripe_customer_id or "",
            success_url=_billing_page(done=True),
            cancel_url=_billing_page(),
        )
    except StripeError as exc:
        logger.warning("Starting a subscription failed: %s", exc)
        raise HTTPException(status_code=502, detail=STRIPE_DOWN) from exc
    return BillingLink(url=url)


@router.post("/{agency_id}/billing/portal", response_model=BillingLink)
async def open_portal(
    session: SessionDep, current_user: CurrentUser, agency_id: uuid.UUID
) -> BillingLink:
    """Stripe's page for the card and billing details."""
    agency = _as_billing_admin(session, current_user.id, agency_id)
    if not agency.stripe_customer_id:
        raise HTTPException(status_code=409, detail="Start the subscription first.")
    try:
        url = await stripe.create_portal(
            customer_id=agency.stripe_customer_id, return_url=_billing_page()
        )
    except StripeError as exc:
        logger.warning("Opening Stripe's portal failed: %s", exc)
        raise HTTPException(status_code=502, detail=STRIPE_DOWN) from exc
    return BillingLink(url=url)


async def _set_ending(
    session: SessionDep, user_id: uuid.UUID, agency_id: uuid.UUID, *, ends: bool
) -> BillingPublic:
    agency = _as_billing_admin(session, user_id, agency_id)
    try:
        agency = await sync_subscription(session, agency)
        if not agency.stripe_subscription_id or agency.subscription_state in (
            SubscriptionState.none,
            SubscriptionState.ended,
        ):
            raise HTTPException(
                status_code=409, detail="This agency has no subscription to change."
            )
        subscription = await stripe.set_ends_at_period_end(
            subscription_id=agency.stripe_subscription_id, ends=ends
        )
    except StripeError as exc:
        logger.warning("Changing a subscription failed: %s", exc)
        raise HTTPException(status_code=502, detail=STRIPE_DOWN) from exc
    agency = crud_billing.store_subscription(
        session=session, agency=agency, subscription=subscription
    )
    return BillingPublic(
        subscription=crud_billing.subscription_public(agency),
        card=None,
        details=None,
        read_from_stripe=True,
    )


@router.post("/{agency_id}/billing/cancel", response_model=BillingPublic)
async def cancel_subscription(
    session: SessionDep, current_user: CurrentUser, agency_id: uuid.UUID
) -> BillingPublic:
    """Cancel: the subscription runs to the end of the paid period and is not
    renewed. Nothing is refunded. The answer leaves out the card and details."""
    return await _set_ending(session, current_user.id, agency_id, ends=True)


@router.post("/{agency_id}/billing/resume", response_model=BillingPublic)
async def resume_subscription(
    session: SessionDep, current_user: CurrentUser, agency_id: uuid.UUID
) -> BillingPublic:
    """Undo a cancellation before the paid period ends."""
    return await _set_ending(session, current_user.id, agency_id, ends=False)
