"""Adding to an agency's balance: top-ups paid by an Admin, and auto top-up.

Both end the same way: Stripe has a paid invoice marked as a top-up, and one line is
added to the agency's ledger for the amount before tax. The line carries the invoice's
id and the database allows one line per invoice, so however often Stripe's messages
repeat or a page is reloaded, a payment is credited once.

Auto top-up charges the saved card with nobody present, when the period's included
amount and the balance are both used up. An agency with it on is not paused in the
minute between running out and the charge (`money_of`). The scheduled run looks at
every agency that has it on; there is no limit on how often it may charge (Decided by
Dmytro, 2026-11-24). After a payment fails nothing is charged again until the card
changes or auto top-up is switched off and on.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col

from app.core.config import settings
from app.models.agency import Agency, SubscriptionState
from app.models.billing import BalanceEntry, BalanceKind
from app.services import stripe
from app.services.billing_notify import send_payment_failed
from app.services.billing_state import money_of
from app.services.stripe import Card, Invoice, StripeDeclined, StripeError

logger = logging.getLogger(__name__)

_KINDS = {"top_up": BalanceKind.top_up, "auto_top_up": BalanceKind.auto_top_up}
_NOTES = {"top_up": "Added funds", "auto_top_up": "Auto top-up"}


def card_mark(card: Card | None) -> str | None:
    """A card as text, to tell later whether it changed."""
    if card is None:
        return None
    return f"{card.brand}:{card.last4}:{card.exp_month}/{card.exp_year}"


def credit_invoice(
    *, session: Session, agency: Agency, invoice: Invoice
) -> Decimal | None:
    """Add a paid top-up invoice to the agency's balance, once. Returns the amount
    credited, also when it had been credited before; None when the invoice is not a
    paid top-up of this agency. Commits."""
    if (
        invoice.status != "paid"
        or invoice.kind not in _KINDS
        or invoice.customer_id != agency.stripe_customer_id
    ):
        return None
    amount = (Decimal(invoice.subtotal_cents) / 100).quantize(Decimal("0.01"))
    session.execute(
        pg_insert(BalanceEntry.__table__)  # type: ignore[attr-defined]
        .values(
            agency_id=agency.id,
            kind=_KINDS[invoice.kind],
            amount_usd=amount,
            note=_NOTES[invoice.kind],
            stripe_invoice_id=invoice.id,
        )
        .on_conflict_do_nothing(index_elements=["stripe_invoice_id"])
    )
    if agency.auto_top_up_invoice_id == invoice.id:
        agency.auto_top_up_invoice_id = None
        session.add(agency)
    session.commit()
    return amount


# A run's claim on an agency's turn, kept where the invoice's id goes once the
# invoice exists: "claim:" and when it was made. A claim older than this belongs to a
# run that died before it made an invoice, and may be taken over.
_CLAIM = "claim:"
_CLAIM_DIES_AFTER = timedelta(minutes=10)


def _claim(session: Session, agency: Agency) -> str | None:
    """Take this agency's turn to be charged, or None when another run has it.
    Decided by the database in one statement, so two runs cannot both win."""
    now = datetime.now(UTC)
    current = agency.auto_top_up_invoice_id
    if current is not None:
        if not current.startswith(_CLAIM):
            return None
        try:
            made = datetime.fromtimestamp(int(current.removeprefix(_CLAIM)), UTC)
        except ValueError:
            made = now - _CLAIM_DIES_AFTER
        if now - made < _CLAIM_DIES_AFTER:
            return None
    claim = f"{_CLAIM}{int(now.timestamp())}"
    held = col(Agency.auto_top_up_invoice_id)
    taken = session.execute(
        update(Agency)
        .where(
            col(Agency.id) == agency.id,
            held.is_(None) if current is None else held == current,
        )
        .values(auto_top_up_invoice_id=claim)
    )
    session.commit()
    session.refresh(agency)
    return claim if taken.rowcount == 1 else None  # type: ignore[attr-defined]


def _has_money(session: Session, agency: Agency) -> bool:
    """Whether anything is left of the period's included amount or of the balance.
    Auto top-up charges only when both are used up (Decided by Dmytro, 2026-11-24)."""
    money = money_of(session=session, agency=agency)
    return money.included_left + money.balance > Decimal("0")


def clear_failure(*, session: Session, agency: Agency) -> None:
    agency.payment_failed_at = None
    agency.payment_failed_amount_usd = None
    agency.payment_failed_reason = None
    agency.payment_failed_card = None
    session.add(agency)
    session.commit()


def _record_failure(
    session: Session, agency: Agency, amount_usd: int, reason: str, card: Card | None
) -> None:
    agency.auto_top_up_invoice_id = None
    agency.payment_failed_at = datetime.now(UTC)
    agency.payment_failed_amount_usd = amount_usd
    agency.payment_failed_reason = reason[:255]
    agency.payment_failed_card = card_mark(card)
    session.add(agency)
    session.commit()


async def auto_top_up(*, session: Session, agency: Agency) -> str:
    """One agency's turn in the scheduled run. Answers what happened: `off`,
    `enough`, `waiting`, `charged`, `failed` or `held` (a payment failed earlier and
    the card has not changed).

    Raises:
        StripeError: Stripe could not be reached; nothing was changed that the next
            run does not pick up.
    """
    customer_id = agency.stripe_customer_id
    if (
        not agency.auto_top_up_enabled
        or not customer_id
        or agency.subscription_state
        not in (SubscriptionState.active, SubscriptionState.past_due)
    ):
        return "off"
    amount_usd = agency.auto_top_up_amount_usd
    invoice_id = agency.auto_top_up_invoice_id
    waiting = invoice_id is not None and not invoice_id.startswith(_CLAIM)
    if not waiting and agency.payment_failed_at is None and _has_money(session, agency):
        # The usual turn: nothing to charge, and nothing asked of Stripe.
        return "enough"

    card, _details = await stripe.card_and_details(
        customer_id=customer_id, subscription_id=agency.stripe_subscription_id
    )
    if agency.payment_failed_at is not None:
        if card is None or card_mark(card) == agency.payment_failed_card:
            return "held"
        clear_failure(session=session, agency=agency)
        if not waiting and _has_money(session, agency):
            return "enough"

    if not waiting:
        # Only one run may make this agency's invoice, or two overlapping runs would
        # each charge the card.
        claim = _claim(session, agency)
        if claim is None:
            return "waiting"
        if card is None:
            _record_failure(session, agency, amount_usd, "No card on file.", None)
            send_payment_failed(session=session, agency=agency)
            return "failed"
        invoice_id = await stripe.start_auto_top_up(
            customer_id=customer_id, amount_cents=amount_usd * 100
        )
        # Kept before the card is charged: a run that dies here is finished by the
        # next one instead of charging again.
        agency.auto_top_up_invoice_id = invoice_id
        session.add(agency)
        session.commit()
    assert invoice_id is not None
    try:
        invoice = await stripe.charge_invoice(invoice_id=invoice_id)
    except StripeDeclined as declined:
        _record_failure(session, agency, amount_usd, declined.reason, card)
        send_payment_failed(session=session, agency=agency)
        return "failed"
    if invoice.status != "paid":
        return "waiting"
    credit_invoice(session=session, agency=agency, invoice=invoice)
    return "charged"


async def run_auto_top_ups(*, session: Session) -> dict[str, int]:
    """Every agency with auto top-up on. One agency's trouble does not stop the rest."""
    counts: dict[str, int] = {}
    if not settings.billing_enabled:
        return counts
    agencies = session.execute(
        select(Agency).where(
            col(Agency.auto_top_up_enabled).is_(True),
            col(Agency.stripe_customer_id).is_not(None),
        )
    ).scalars()
    for agency in list(agencies):
        try:
            outcome = await auto_top_up(session=session, agency=agency)
        except StripeError as exc:
            session.rollback()
            logger.warning("Auto top-up could not reach Stripe: %s", exc)
            outcome = "unreachable"
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts
