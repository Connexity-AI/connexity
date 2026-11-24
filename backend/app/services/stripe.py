"""Stripe, over its REST API: the agency's subscription and the pages that take a card.

Connexity never sees a card number. A person pays, changes the card and edits billing
details on Stripe's own pages (Checkout and the customer portal); this module makes the
links to them and reads back what Stripe then knows.

Every call raises `StripeError` on a timeout, a refusal, or an answer that is not what
Stripe documents. The error's text is Stripe's own message when there is one.
"""

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.models.agency import SubscriptionState

_API = "https://api.stripe.com/v1"
# The API version this code was written against. In it a subscription's period sits on
# its items; `_period` also reads the older place.
_VERSION = "2025-09-30.clover"
_TIMEOUT = httpx.Timeout(15.0)
# How old a signed message may be (Stripe's own default).
SIGNATURE_MAX_AGE_SECONDS = 5 * 60


class StripeError(Exception):
    """Stripe could not be reached, refused, or answered something unexpected."""

    # Stripe answered that the card was refused (HTTP 402), as opposed to not being
    # reachable or the request being wrong.
    refused: bool = False


@dataclass(frozen=True)
class Subscription:
    id: str
    state: SubscriptionState
    period_start: datetime | None
    period_end: datetime | None
    ends_at_period_end: bool
    created: int


@dataclass(frozen=True)
class Card:
    brand: str
    last4: str
    exp_month: int
    exp_year: int


@dataclass(frozen=True)
class Details:
    name: str | None
    address: list[str]
    tax_ids: list[str]


# What Stripe calls a subscription's status, as Connexity's states. `incomplete` is a
# first payment that has not gone through: no subscription yet. `canceled` is over.
_STATES = {
    "active": SubscriptionState.active,
    "trialing": SubscriptionState.active,
    "past_due": SubscriptionState.past_due,
    "unpaid": SubscriptionState.unpaid,
    "paused": SubscriptionState.unpaid,
    "canceled": SubscriptionState.ended,
    "incomplete": SubscriptionState.none,
    "incomplete_expired": SubscriptionState.none,
}


# Which subscription speaks for a customer who has several: one that is paid for or
# owed comes before a first payment that never finished, and that before one that
# ended. Among equals, the newest.
_RANK = {
    SubscriptionState.active: 2,
    SubscriptionState.past_due: 2,
    SubscriptionState.unpaid: 2,
    SubscriptionState.none: 1,
    SubscriptionState.ended: 0,
}


async def _request(
    method: str, path: str, *, data: dict[str, str] | None = None
) -> dict[str, Any]:
    key = (settings.STRIPE_SECRET_KEY or "").strip()
    if not key:
        raise StripeError("Stripe is not set up")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.request(
                method,
                f"{_API}{path}",
                data=data if method != "GET" else None,
                params=data if method == "GET" else None,
                auth=(key, ""),
                headers={"Stripe-Version": _VERSION},
            )
    except httpx.HTTPError as exc:
        raise StripeError(f"Stripe could not be reached: {type(exc).__name__}") from exc
    try:
        body = response.json()
    except ValueError as exc:
        raise StripeError("Stripe's answer could not be read") from exc
    if not isinstance(body, dict):
        raise StripeError("Stripe's answer could not be read")
    if response.status_code >= 400:
        error = body.get("error")
        message = error.get("message") if isinstance(error, dict) else None
        failure = StripeError(str(message or f"Stripe answered {response.status_code}"))
        failure.refused = response.status_code == 402
        raise failure
    return body


def _text(body: dict[str, Any], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value:
        raise StripeError(f"Stripe's answer has no {key}")
    return value


def _moment(value: object) -> datetime | None:
    return datetime.fromtimestamp(value, UTC) if isinstance(value, int) else None


def _period(body: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    items = body.get("items")
    rows = items.get("data") if isinstance(items, dict) else None
    first = rows[0] if isinstance(rows, list) and rows else None
    source = (
        first if isinstance(first, dict) and "current_period_end" in first else body
    )
    return (
        _moment(source.get("current_period_start")),
        _moment(source.get("current_period_end")),
    )


def read_subscription(body: dict[str, Any]) -> Subscription:
    """A subscription from Stripe's answer.

    Raises:
        StripeError: the answer is not a subscription Connexity can read.
    """
    status = body.get("status")
    if status not in _STATES:
        raise StripeError(f"Stripe's subscription has an unknown status: {status!r}")
    start, end = _period(body)
    created = body.get("created")
    return Subscription(
        id=_text(body, "id"),
        state=_STATES[status],
        period_start=start,
        period_end=end,
        ends_at_period_end=bool(body.get("cancel_at_period_end"))
        or body.get("cancel_at") is not None,
        created=created if isinstance(created, int) else 0,
    )


async def create_customer(*, name: str, agency_id: str) -> str:
    body = await _request(
        "POST", "/customers", data={"name": name, "metadata[agency_id]": agency_id}
    )
    return _text(body, "id")


async def create_checkout(
    *, customer_id: str, success_url: str, cancel_url: str
) -> str:
    """A Checkout page that starts the one subscription. Answers its address."""
    data = {
        "mode": "subscription",
        "customer": customer_id,
        "line_items[0][price]": (settings.STRIPE_PRICE_ID or "").strip(),
        "line_items[0][quantity]": "1",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "billing_address_collection": "required",
        "tax_id_collection[enabled]": "true",
        # Checkout may save what the person types there onto the customer; tax and
        # tax IDs need the address and the name.
        "customer_update[address]": "auto",
        "customer_update[name]": "auto",
    }
    if settings.STRIPE_AUTOMATIC_TAX:
        data["automatic_tax[enabled]"] = "true"
    return _text(await _request("POST", "/checkout/sessions", data=data), "url")


async def expire_open_checkouts(*, customer_id: str) -> int:
    """Close every Checkout page of the customer that could still be paid, so two
    pages can never both start a subscription. Answers how many were closed."""
    body = await _request(
        "GET",
        "/checkout/sessions",
        data={"customer": customer_id, "status": "open", "limit": "100"},
    )
    rows = body.get("data")
    if not isinstance(rows, list):
        raise StripeError("Stripe's answer has no Checkout sessions")
    closed = 0
    for row in rows:
        session_id = row.get("id") if isinstance(row, dict) else None
        if isinstance(session_id, str) and session_id:
            await _request("POST", f"/checkout/sessions/{session_id}/expire")
            closed += 1
    return closed


async def create_portal(*, customer_id: str, return_url: str) -> str:
    """Stripe's page for the card and billing details. Answers its address."""
    body = await _request(
        "POST",
        "/billing_portal/sessions",
        data={"customer": customer_id, "return_url": return_url},
    )
    return _text(body, "url")


async def current_subscription(*, customer_id: str) -> Subscription | None:
    """The customer's subscription: the one paid for or owed if there is one, otherwise
    an unfinished first payment, otherwise the latest that ended. None when they never
    had one."""
    body = await _request(
        "GET",
        "/subscriptions",
        data={"customer": customer_id, "status": "all", "limit": "20"},
    )
    rows = body.get("data")
    if not isinstance(rows, list):
        raise StripeError("Stripe's answer has no subscriptions")
    found = [read_subscription(row) for row in rows if isinstance(row, dict)]
    if not found:
        return None
    return max(found, key=lambda s: (_RANK[s.state], s.created))


async def set_ends_at_period_end(*, subscription_id: str, ends: bool) -> Subscription:
    """Cancel at the end of the paid period, or undo that."""
    body = await _request(
        "POST",
        f"/subscriptions/{subscription_id}",
        data={"cancel_at_period_end": "true" if ends else "false"},
    )
    return read_subscription(body)


def _card(method: object) -> Card | None:
    card = method.get("card") if isinstance(method, dict) else None
    if not isinstance(card, dict):
        return None
    try:
        return Card(
            brand=str(card["brand"]),
            last4=str(card["last4"]),
            exp_month=int(card["exp_month"]),
            exp_year=int(card["exp_year"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


async def card_and_details(
    *, customer_id: str, subscription_id: str | None
) -> tuple[Card | None, Details]:
    """The card that is charged (the subscription's, else the customer's default) and
    the billing details that appear on invoices."""
    customer = await _request(
        "GET",
        f"/customers/{customer_id}",
        data={
            "expand[0]": "invoice_settings.default_payment_method",
            "expand[1]": "tax_ids",
        },
    )
    invoice_settings = customer.get("invoice_settings")
    card = _card(
        invoice_settings.get("default_payment_method")
        if isinstance(invoice_settings, dict)
        else None
    )
    if card is None and subscription_id:
        subscription = await _request(
            "GET",
            f"/subscriptions/{subscription_id}",
            data={"expand[0]": "default_payment_method"},
        )
        card = _card(subscription.get("default_payment_method"))
    address = customer.get("address")
    lines: list[str] = []
    if isinstance(address, dict):
        street = [address.get("line1"), address.get("line2")]
        place = " ".join(
            str(part)
            for part in (
                address.get("city"),
                address.get("state"),
                address.get("postal_code"),
            )
            if part
        )
        lines = [str(part) for part in (*street, place, address.get("country")) if part]
    tax_ids = customer.get("tax_ids")
    rows = tax_ids.get("data") if isinstance(tax_ids, dict) else None
    numbers = [
        str(row["value"])
        for row in (rows if isinstance(rows, list) else [])
        if isinstance(row, dict) and row.get("value")
    ]
    name = customer.get("name")
    return card, Details(
        name=name if isinstance(name, str) and name else None,
        address=lines,
        tax_ids=numbers,
    )


def signature_is_valid(
    *, raw_body: bytes, header: str | None, secret: str, now: float | None = None
) -> bool:
    """Stripe signs ``timestamp.raw body`` with HMAC-SHA256, keyed by the endpoint's
    secret, and sends ``t=<timestamp>,v1=<signature>``; a rolled secret adds a second
    ``v1``."""
    if not header or not secret:
        return False
    timestamp: str | None = None
    signatures: list[str] = []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)
    if timestamp is None or not timestamp.isdigit() or not signatures:
        return False
    current = time.time() if now is None else now
    if abs(current - int(timestamp)) > SIGNATURE_MAX_AGE_SECONDS:
        return False
    expected = hmac.new(
        secret.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256
    ).hexdigest()
    return any(hmac.compare_digest(expected, given) for given in signatures)


# ── Top-ups and invoices ──


class StripeDeclined(StripeError):
    """Stripe tried to charge and the payment did not go through."""

    def __init__(self, reason: str, invoice_id: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.invoice_id = invoice_id


@dataclass(frozen=True)
class Invoice:
    id: str
    customer_id: str | None
    # Stripe's own: draft, open, paid, void or uncollectible.
    status: str
    # What the invoice is for: `subscription`, `top_up`, `auto_top_up` or `other`.
    kind: str
    subtotal_cents: int
    total_cents: int
    created: datetime | None
    url: str | None


@dataclass(frozen=True)
class CheckoutSession:
    id: str
    customer_id: str | None
    paid: bool
    invoice_id: str | None


def read_invoice(body: dict[str, Any]) -> Invoice:
    """An invoice from Stripe's answer.

    Raises:
        StripeError: the answer is not an invoice Connexity can read.
    """
    status = body.get("status")
    subtotal, total = body.get("subtotal"), body.get("total")
    if (
        not isinstance(status, str)
        or not isinstance(subtotal, int)
        or not isinstance(total, int)
    ):
        raise StripeError("Stripe's invoice could not be read")
    metadata = body.get("metadata")
    marked = metadata.get("kind") if isinstance(metadata, dict) else None
    reason = body.get("billing_reason")
    if marked in ("top_up", "auto_top_up"):
        kind = str(marked)
    elif isinstance(reason, str) and reason.startswith("subscription"):
        kind = "subscription"
    else:
        kind = "other"
    customer = body.get("customer")
    url = body.get("hosted_invoice_url")
    return Invoice(
        id=_text(body, "id"),
        customer_id=customer if isinstance(customer, str) else None,
        status=status,
        kind=kind,
        subtotal_cents=subtotal,
        total_cents=total,
        created=_moment(body.get("created")),
        url=url if isinstance(url, str) and url else None,
    )


async def create_top_up_checkout(
    *, customer_id: str, amount_cents: int, success_url: str, cancel_url: str
) -> str:
    """A Checkout page for a one-time payment that adds to the balance. Stripe makes
    an invoice for it, marked as a top-up. Answers the page's address."""
    data = {
        "mode": "payment",
        "customer": customer_id,
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": str(amount_cents),
        "line_items[0][price_data][product_data][name]": "Connexity balance",
        "line_items[0][quantity]": "1",
        "invoice_creation[enabled]": "true",
        "invoice_creation[invoice_data][description]": "Added funds",
        "invoice_creation[invoice_data][metadata][kind]": "top_up",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "billing_address_collection": "required",
        "tax_id_collection[enabled]": "true",
        "customer_update[address]": "auto",
        "customer_update[name]": "auto",
    }
    if settings.STRIPE_AUTOMATIC_TAX:
        data["automatic_tax[enabled]"] = "true"
    return _text(await _request("POST", "/checkout/sessions", data=data), "url")


async def get_checkout(*, session_id: str) -> CheckoutSession:
    body = await _request("GET", f"/checkout/sessions/{session_id}")
    customer, invoice = body.get("customer"), body.get("invoice")
    return CheckoutSession(
        id=_text(body, "id"),
        customer_id=customer if isinstance(customer, str) else None,
        paid=body.get("payment_status") == "paid",
        invoice_id=invoice if isinstance(invoice, str) else None,
    )


async def get_invoice(*, invoice_id: str) -> Invoice:
    return read_invoice(await _request("GET", f"/invoices/{invoice_id}"))


async def list_invoices(*, customer_id: str, limit: int = 100) -> list[Invoice]:
    """The customer's invoices, newest first. Drafts are left out."""
    body = await _request(
        "GET", "/invoices", data={"customer": customer_id, "limit": str(limit)}
    )
    rows = body.get("data")
    if not isinstance(rows, list):
        raise StripeError("Stripe's answer has no invoices")
    found = [read_invoice(row) for row in rows if isinstance(row, dict)]
    return [invoice for invoice in found if invoice.status != "draft"]


async def start_auto_top_up(*, customer_id: str, amount_cents: int) -> str:
    """An invoice for an automatic top-up, ready to be charged. Answers its id, which
    the caller keeps before charging, so a charge is never made twice."""
    data = {
        "customer": customer_id,
        "collection_method": "charge_automatically",
        "auto_advance": "false",
        "description": "Auto top-up",
        "metadata[kind]": "auto_top_up",
    }
    if settings.STRIPE_AUTOMATIC_TAX:
        data["automatic_tax[enabled]"] = "true"
    invoice_id = _text(await _request("POST", "/invoices", data=data), "id")
    await _request(
        "POST",
        "/invoiceitems",
        data={
            "customer": customer_id,
            "invoice": invoice_id,
            "amount": str(amount_cents),
            "currency": "usd",
            "description": "Connexity balance",
        },
    )
    return invoice_id


async def charge_invoice(*, invoice_id: str) -> Invoice:
    """Charge the customer's saved card for an invoice.

    Raises:
        StripeDeclined: the card was refused; the invoice is voided so it cannot be
            charged later by itself.
        StripeError: Stripe could not be reached; the invoice is left as it is.
    """
    current = await get_invoice(invoice_id=invoice_id)
    if current.status == "paid":
        return current
    if current.status in ("void", "uncollectible"):
        raise StripeDeclined("The payment did not go through.", invoice_id)
    if current.status == "draft":
        await _request("POST", f"/invoices/{invoice_id}/finalize")
    try:
        return read_invoice(await _request("POST", f"/invoices/{invoice_id}/pay"))
    except StripeError as exc:
        if not getattr(exc, "refused", False):
            raise
        await _request("POST", f"/invoices/{invoice_id}/void")
        raise StripeDeclined(str(exc), invoice_id) from exc
