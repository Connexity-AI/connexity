"""Agency settings › Billing: the subscription, the card and billing details.

Only Admins. Paying, the card and the billing details happen on Stripe's pages; these
routes answer the links to them and what Stripe then knows. Without Stripe's settings
every route answers 404 and the web app shows no Billing section.
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.agencies import _mine
from app.core.config import settings
from app.crud import billing as crud_billing
from app.models import (
    AgencyUsagePublic,
    AutoTopUpPublic,
    AutoTopUpUpdate,
    BillingDetailsPublic,
    BillingLink,
    BillingPublic,
    CardPublic,
    FailedPaymentPublic,
    InvoicePublic,
    MoneyPublic,
    TopUpConfirm,
    TopUpRequest,
    TopUpResult,
)
from app.models.agency import Agency, AgencyRole, SubscriptionState
from app.services import stripe
from app.services.billing_state import money_public
from app.services.billing_usage import PeriodKey, agency_usage, as_csv
from app.services.stripe import StripeError
from app.services.top_up import card_mark, clear_failure, credit_invoice

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


_INVOICE_WORDS = {
    "subscription": "Subscription",
    "top_up": "Added funds",
    "auto_top_up": "Auto top-up",
}


def _invoice_public(invoice: stripe.Invoice) -> InvoicePublic:
    if invoice.status == "paid":
        status = "paid"
    elif invoice.status == "open":
        status = "processing"
    else:
        status = "failed"
    return InvoicePublic(
        id=invoice.id,
        created_at=invoice.created or datetime.now(UTC),
        description=_INVOICE_WORDS.get(invoice.kind, "Invoice"),
        amount_usd=invoice.total_cents / 100,
        status=status,
        url=invoice.url,
    )


def _card_public(card: stripe.Card) -> CardPublic:
    today = datetime.now(UTC)
    months_left = (card.exp_year - today.year) * 12 + card.exp_month - today.month
    return CardPublic(**card.__dict__, expires_soon=months_left <= 1)


def _auto_top_up_public(agency: Agency) -> AutoTopUpPublic:
    return AutoTopUpPublic(
        enabled=agency.auto_top_up_enabled,
        amount_usd=agency.auto_top_up_amount_usd,
    )


def _failed_public(agency: Agency) -> FailedPaymentPublic | None:
    if agency.payment_failed_at is None:
        return None
    return FailedPaymentPublic(
        amount_usd=agency.payment_failed_amount_usd or 0,
        reason=agency.payment_failed_reason or "The payment did not go through.",
        at=agency.payment_failed_at,
    )


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


@router.get("/{agency_id}/billing/status", response_model=MoneyPublic | None)
def read_status(
    session: SessionDep, current_user: CurrentUser, agency_id: uuid.UUID
) -> MoneyPublic | None:
    """What the agency has left and whether it is paused, for the stripe at the top of
    the app and the sidebar's line. Anyone in the agency. Null where paying is not set
    up: nothing pauses there."""
    agency, _ = _mine(session, current_user.id, agency_id)
    return money_public(session=session, agency_id=agency.id)


@router.get("/{agency_id}/billing/usage", response_model=AgencyUsagePublic)
def read_usage(
    session: SessionDep,
    current_user: CurrentUser,
    agency_id: uuid.UUID,
    period: PeriodKey | None = None,
) -> AgencyUsagePublic:
    """What the agency used in a period, per workspace and agent, at list price. `this`
    and `last` are the subscription's periods; without a subscription only `30d`
    exists. Counted the way the money is drawn, so `this` is what came off the
    included amount and the balance."""
    agency = _as_billing_admin(session, current_user.id, agency_id)
    return agency_usage(session=session, agency=agency, period=period)


@router.get("/{agency_id}/billing/usage.csv", response_class=Response)
def download_usage(
    session: SessionDep,
    current_user: CurrentUser,
    agency_id: uuid.UUID,
    period: PeriodKey | None = None,
) -> Response:
    """The same usage as a CSV, one row per workspace and agent, to bill each client."""
    agency = _as_billing_admin(session, current_user.id, agency_id)
    usage = agency_usage(session=session, agency=agency, period=period)
    name = f"connexity-usage-{usage.period.starts_at:%Y-%m-%d}.csv"
    return Response(
        content=as_csv(usage),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/{agency_id}/billing", response_model=BillingPublic)
async def read_billing(
    session: SessionDep, current_user: CurrentUser, agency_id: uuid.UUID
) -> BillingPublic:
    """The subscription, read again from Stripe, with the card and billing details.
    When Stripe cannot be reached, the last known subscription without them."""
    agency = _as_billing_admin(session, current_user.id, agency_id)
    card = details = None
    invoices: list[InvoicePublic] = []
    fresh = True
    if agency.stripe_customer_id:
        try:
            agency = await sync_subscription(session, agency)
            found, about = await stripe.card_and_details(
                customer_id=agency.stripe_customer_id or "",
                subscription_id=agency.stripe_subscription_id,
            )
            listed = await stripe.list_invoices(
                customer_id=agency.stripe_customer_id or ""
            )
            # A paid top-up whose message never arrived is credited here.
            for invoice in listed:
                credit_invoice(session=session, agency=agency, invoice=invoice)
            if (
                agency.payment_failed_at is not None
                and found is not None
                and card_mark(found) != agency.payment_failed_card
            ):
                clear_failure(session=session, agency=agency)
            card = _card_public(found) if found else None
            details = BillingDetailsPublic(**about.__dict__)
            invoices = [_invoice_public(invoice) for invoice in listed]
        except StripeError as exc:
            logger.warning("Billing could not be read from Stripe: %s", exc)
            fresh = False
    return BillingPublic(
        subscription=crud_billing.subscription_public(agency),
        card=card,
        details=details,
        invoices=invoices,
        auto_top_up=_auto_top_up_public(agency),
        failed_payment=_failed_public(agency),
        sales_contact_url=(settings.SALES_CONTACT_URL or "").strip() or None,
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
        auto_top_up=_auto_top_up_public(agency),
        failed_payment=_failed_public(agency),
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


@router.post("/{agency_id}/billing/top-up", response_model=BillingLink)
async def start_top_up(
    session: SessionDep,
    current_user: CurrentUser,
    agency_id: uuid.UUID,
    body: TopUpRequest,
) -> BillingLink:
    """Stripe's page to add funds to the balance: $50 to $10,000. For an agency with a
    subscription. The balance is credited when Stripe says the payment went through."""
    agency = _as_billing_admin(session, current_user.id, agency_id)
    if not agency.stripe_customer_id or agency.subscription_state not in (
        SubscriptionState.active,
        SubscriptionState.past_due,
    ):
        raise HTTPException(status_code=409, detail="Start the subscription first.")
    site = _billing_page()
    try:
        url = await stripe.create_top_up_checkout(
            customer_id=agency.stripe_customer_id,
            amount_cents=body.amount_usd * 100,
            success_url=f"{site}&topup={{CHECKOUT_SESSION_ID}}",
            cancel_url=site,
        )
    except StripeError as exc:
        logger.warning("Starting a top-up failed: %s", exc)
        raise HTTPException(status_code=502, detail=STRIPE_DOWN) from exc
    return BillingLink(url=url)


@router.post("/{agency_id}/billing/top-up/confirm", response_model=TopUpResult)
async def confirm_top_up(
    session: SessionDep,
    current_user: CurrentUser,
    agency_id: uuid.UUID,
    body: TopUpConfirm,
) -> TopUpResult:
    """What became of a top-up the person has just come back from: `paid` with the
    amount added, or `processing`. Credits the balance if Stripe's message has not
    done so yet; a payment is never credited twice."""
    agency = _as_billing_admin(session, current_user.id, agency_id)
    try:
        checkout = await stripe.get_checkout(session_id=body.session_id)
        if (
            not agency.stripe_customer_id
            or checkout.customer_id != agency.stripe_customer_id
        ):
            raise HTTPException(status_code=404, detail="Payment not found")
        if not checkout.paid or checkout.invoice_id is None:
            return TopUpResult(status="processing", amount_usd=None)
        invoice = await stripe.get_invoice(invoice_id=checkout.invoice_id)
    except StripeError as exc:
        logger.warning("A top-up could not be confirmed: %s", exc)
        raise HTTPException(status_code=502, detail=STRIPE_DOWN) from exc
    added = credit_invoice(session=session, agency=agency, invoice=invoice)
    if added is None:
        return TopUpResult(status="processing", amount_usd=None)
    return TopUpResult(status="paid", amount_usd=float(added))


@router.put("/{agency_id}/billing/auto-top-up", response_model=AutoTopUpPublic)
async def set_auto_top_up(
    session: SessionDep,
    current_user: CurrentUser,
    agency_id: uuid.UUID,
    body: AutoTopUpUpdate,
) -> AutoTopUpPublic:
    """Switch auto top-up on or off and set its amount. Turning it on needs a
    card on file, and forgets an earlier failed payment so the card is tried again."""
    agency = _as_billing_admin(session, current_user.id, agency_id)
    if body.enabled:
        if not agency.stripe_customer_id:
            raise HTTPException(status_code=409, detail="Start the subscription first.")
        try:
            card, _ = await stripe.card_and_details(
                customer_id=agency.stripe_customer_id,
                subscription_id=agency.stripe_subscription_id,
            )
        except StripeError as exc:
            logger.warning("Auto top-up could not check the card: %s", exc)
            raise HTTPException(status_code=502, detail=STRIPE_DOWN) from exc
        if card is None:
            raise HTTPException(status_code=409, detail="Add a card first.")
    switched_on = body.enabled and not agency.auto_top_up_enabled
    agency.auto_top_up_enabled = body.enabled
    agency.auto_top_up_amount_usd = body.amount_usd
    session.add(agency)
    session.commit()
    session.refresh(agency)
    if switched_on and agency.payment_failed_at is not None:
        clear_failure(session=session, agency=agency)
    return _auto_top_up_public(agency)
