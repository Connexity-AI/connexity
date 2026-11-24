"""Top-ups, auto top-up, invoices and the emails about money, through the API.

Stripe is an invented account kept in memory (`FakeStripe`); no request leaves the
machine. Customers, cards and invoices are invented.
"""

import re
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User
from app.models.agency import Agency, AgencyMember, AgencyRole
from app.models.billing import AgencyState, BalanceEntry, BalanceKind
from app.services import billing_notify, billing_state, top_up
from app.tests.api.routes.test_balance_and_pause import (
    _agency,
    _cookies,
    _subscribe,
    _use,
)
from app.tests.api.routes.test_billing import _post_event, _subscription
from app.tests.api.routes.test_mcp_scan_calls import (
    ISSUER,
    MCP_URL,
    _headers,
    _person,
)

API = settings.API_V1_STR
STRIPE = "https://api.stripe.com/v1"


@pytest.fixture(autouse=True)
def _paying_is_set_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_invented")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID", "price_invented")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    monkeypatch.setattr(settings, "STRIPE_AUTOMATIC_TAX", True)
    monkeypatch.setattr(settings, "SITE_URL", "https://app.example.com")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)


@pytest.fixture(autouse=True)
def _only_this_tests_agencies(db: Session) -> None:
    """The scheduled steps look at every agency. Agencies left by earlier tests are
    taken out of their reach, so each test sees only its own."""
    db.execute(
        update(Agency).values(auto_top_up_enabled=False, first_subscribed_at=None)
    )
    db.commit()


class Outbox:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def __call__(self, *, email_to: str, subject: str, html_content: str) -> bool:
        self.sent.append({"to": email_to, "subject": subject, "html": html_content})
        return True

    def subjects(self) -> list[str]:
        return [m["subject"] for m in self.sent]


@pytest.fixture
def outbox() -> Generator[Outbox, None, None]:
    box = Outbox()
    with patch("app.services.billing_notify.send_email", box):
        yield box


def _form(request: httpx.Request) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


class FakeStripe:
    """An invented Stripe account: one customer's card, invoices and Checkout pages."""

    def __init__(self, customer_id: str) -> None:
        self.customer_id = customer_id
        self.card: dict[str, Any] | None = {
            "brand": "visa",
            "last4": "4242",
            "exp_month": 8,
            "exp_year": 2099,
        }
        self.declines = False
        self.tax_rate = Decimal("0")
        self.invoices: dict[str, dict[str, Any]] = {}
        self.checkouts: dict[str, dict[str, Any]] = {}
        self.calls: list[str] = []
        self.sent: list[dict[str, str]] = []

    # ── what a test arranges ──

    def invoice(self, kind: str, subtotal: int, status: str = "paid") -> str:
        invoice_id = f"in_{uuid.uuid4().hex[:14]}"
        total = int(subtotal * (1 + self.tax_rate))
        self.invoices[invoice_id] = {
            "id": invoice_id,
            "customer": self.customer_id,
            "status": status,
            "subtotal": subtotal,
            "total": total,
            "created": int(datetime.now(UTC).timestamp()) + len(self.invoices),
            "metadata": {"kind": kind} if kind != "subscription" else {},
            "billing_reason": "subscription_cycle"
            if kind == "subscription"
            else "manual",
            "hosted_invoice_url": f"https://invoice.stripe.com/i/{invoice_id}",
        }
        return invoice_id

    def paid_checkout(self, subtotal: int) -> str:
        session_id = f"cs_{uuid.uuid4().hex[:14]}"
        self.checkouts[session_id] = {
            "id": session_id,
            "customer": self.customer_id,
            "payment_status": "paid",
            "invoice": self.invoice("top_up", subtotal),
        }
        return session_id

    # ── what Stripe answers ──

    def _customer(self, request: httpx.Request) -> httpx.Response:
        method = {"id": "pm_1", "card": self.card} if self.card else None
        return httpx.Response(
            200,
            json={
                "id": self.customer_id,
                "name": "Signal Voice Inc.",
                "address": None,
                "invoice_settings": {"default_payment_method": method},
                "tax_ids": {"data": []},
            },
        )

    def _new_invoice(self, request: httpx.Request) -> httpx.Response:
        sent = _form(request)
        self.sent.append(sent)
        invoice_id = self.invoice(sent["metadata[kind]"], 0, status="draft")
        return httpx.Response(200, json=self.invoices[invoice_id])

    def _new_item(self, request: httpx.Request) -> httpx.Response:
        sent = _form(request)
        self.sent.append(sent)
        invoice = self.invoices[sent["invoice"]]
        invoice["subtotal"] = int(sent["amount"])
        invoice["total"] = int(int(sent["amount"]) * (1 + self.tax_rate))
        return httpx.Response(200, json={"id": "ii_1"})

    def _act(
        self, request: httpx.Request, invoice_id: str, action: str
    ) -> httpx.Response:
        self.calls.append(f"{action}:{invoice_id}")
        invoice = self.invoices[invoice_id]
        if action == "finalize":
            invoice["status"] = "open"
        elif action == "void":
            invoice["status"] = "void"
        elif self.declines:
            return httpx.Response(
                402,
                json={
                    "error": {
                        "code": "card_declined",
                        "message": "Your card was declined.",
                    }
                },
            )
        else:
            invoice["status"] = "paid"
        return httpx.Response(200, json=invoice)

    def _get_invoice(self, request: httpx.Request, invoice_id: str) -> httpx.Response:
        found = self.invoices.get(invoice_id)
        return httpx.Response(200 if found else 404, json=found or {"error": {}})

    def _list_invoices(self, request: httpx.Request) -> httpx.Response:
        rows = sorted(self.invoices.values(), key=lambda i: -i["created"])
        return httpx.Response(200, json={"data": rows})

    def _new_checkout(self, request: httpx.Request) -> httpx.Response:
        self.sent.append(_form(request))
        return httpx.Response(
            200,
            json={"id": "cs_new", "url": "https://checkout.stripe.com/c/pay/cs_new"},
        )

    def _get_checkout(self, request: httpx.Request, session_id: str) -> httpx.Response:
        found = self.checkouts.get(session_id)
        return httpx.Response(200 if found else 404, json=found or {"error": {}})

    def mock(self) -> "FakeStripe":
        respx.get(f"{STRIPE}/customers/{self.customer_id}").mock(
            side_effect=self._customer
        )
        # A subscription whose period is the current one, as the tests' agencies have.
        start = int((datetime.now(UTC) - timedelta(days=10)).timestamp())
        running = _subscription(
            items={
                "data": [
                    {
                        "current_period_start": start,
                        "current_period_end": start + 30 * 86400,
                    }
                ]
            }
        )
        respx.get(f"{STRIPE}/subscriptions").mock(
            return_value=httpx.Response(200, json={"data": [running]})
        )
        respx.get(url__regex=rf"{re.escape(STRIPE)}/subscriptions/.+").mock(
            return_value=httpx.Response(200, json=_subscription())
        )
        respx.post(f"{STRIPE}/invoices").mock(side_effect=self._new_invoice)
        respx.post(f"{STRIPE}/invoiceitems").mock(side_effect=self._new_item)
        respx.post(
            url__regex=rf"{re.escape(STRIPE)}/invoices/(?P<invoice_id>[^/]+)/(?P<action>finalize|pay|void)"
        ).mock(side_effect=self._act)
        respx.get(
            url__regex=rf"{re.escape(STRIPE)}/invoices/(?P<invoice_id>[^/?]+)$"
        ).mock(side_effect=self._get_invoice)
        respx.get(f"{STRIPE}/invoices").mock(side_effect=self._list_invoices)
        respx.post(f"{STRIPE}/checkout/sessions").mock(side_effect=self._new_checkout)
        respx.get(
            url__regex=rf"{re.escape(STRIPE)}/checkout/sessions/(?P<session_id>[^/?]+)$"
        ).mock(side_effect=self._get_checkout)
        return self


def _paying(
    db: Session, name: str | None = None, *, mock: bool = True
) -> tuple[User, Agency, FakeStripe]:
    """An agency with a running subscription and its invented Stripe account. With
    `mock` off the account answers nothing, for a second agency in one test."""
    user = _person(db)
    if name:
        user.full_name = name
        db.add(user)
        db.commit()
    agency = _agency(db, user)
    agency.stripe_customer_id = f"cus_{uuid.uuid4().hex[:12]}"
    db.add(agency)
    db.commit()
    agency = _subscribe(db, agency)
    account = FakeStripe(agency.stripe_customer_id or "")
    return user, agency, account.mock() if mock else account


def _balance(db: Session, agency: Agency) -> Decimal:
    db.expire_all()
    money = billing_state.state_of(session=db, agency_id=agency.id)
    assert money is not None
    return money.balance


def _lines(
    db: Session, agency: Agency
) -> list[tuple[BalanceKind, Decimal, str | None]]:
    db.expire_all()
    rows = db.exec(
        select(BalanceEntry)
        .where(BalanceEntry.agency_id == agency.id)
        .order_by(BalanceEntry.created_at)  # type: ignore[arg-type]
    ).all()
    return [(r.kind, r.amount_usd, r.stripe_invoice_id) for r in rows]


def _invoice_event(kind: str, account: FakeStripe, invoice_id: str) -> dict[str, Any]:
    return {
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "object": "event",
        "type": kind,
        "data": {"object": dict(account.invoices[invoice_id])},
    }


# ── Add funds ──


@respx.mock
def test_adding_funds_opens_stripes_page_for_the_amount(
    client: TestClient, db: Session
) -> None:
    user, agency, account = _paying(db)
    path = f"{API}/agencies/{agency.id}/billing/top-up"

    started = client.post(path, json={"amount_usd": 500}, cookies=_cookies(db, user))
    too_little = client.post(path, json={"amount_usd": 49}, cookies=_cookies(db, user))
    too_much = client.post(path, json={"amount_usd": 10001}, cookies=_cookies(db, user))

    assert started.status_code == 200, started.text
    assert started.json() == {"url": "https://checkout.stripe.com/c/pay/cs_new"}
    sent = account.sent[0]
    assert sent["mode"] == "payment"
    assert sent["customer"] == agency.stripe_customer_id
    assert sent["line_items[0][price_data][unit_amount]"] == "50000"
    assert sent["line_items[0][price_data][currency]"] == "usd"
    assert sent["invoice_creation[enabled]"] == "true"
    assert sent["invoice_creation[invoice_data][metadata][kind]"] == "top_up"
    assert sent["automatic_tax[enabled]"] == "true"
    assert sent["success_url"] == (
        "https://app.example.com/agency/?section=billing&topup={CHECKOUT_SESSION_ID}"
    )
    assert too_little.status_code == too_much.status_code == 422
    assert len(account.sent) == 1


@respx.mock
def test_funds_cannot_be_added_before_there_is_a_subscription(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agency = _agency(db, user)

    r = client.post(
        f"{API}/agencies/{agency.id}/billing/top-up",
        json={"amount_usd": 100},
        cookies=_cookies(db, user),
    )

    assert r.status_code == 409
    assert not respx.calls


@respx.mock
def test_a_paid_top_up_is_credited_once_for_the_amount_before_tax(
    client: TestClient, db: Session
) -> None:
    user, agency, account = _paying(db)
    account.tax_rate = Decimal("0.13")
    invoice_id = account.invoice("top_up", 50000)

    first = _post_event(client, _invoice_event("invoice.paid", account, invoice_id))
    # Stripe sends more than one message about the same payment.
    again = _post_event(
        client, _invoice_event("invoice.payment_succeeded", account, invoice_id)
    )

    assert first.status_code == again.status_code == 200
    assert account.invoices[invoice_id]["total"] == 56500
    assert _lines(db, agency) == [(BalanceKind.top_up, Decimal("500.00"), invoice_id)]
    assert _balance(db, agency) == Decimal("500.00")


@respx.mock
def test_coming_back_from_stripe_credits_it_before_the_message_and_never_twice(
    client: TestClient, db: Session
) -> None:
    user, agency, account = _paying(db)
    session_id = account.paid_checkout(10000)
    invoice_id = account.checkouts[session_id]["invoice"]
    path = f"{API}/agencies/{agency.id}/billing/top-up/confirm"

    back = client.post(
        path, json={"session_id": session_id}, cookies=_cookies(db, user)
    )
    reloaded = client.post(
        path, json={"session_id": session_id}, cookies=_cookies(db, user)
    )
    _post_event(client, _invoice_event("invoice.paid", account, invoice_id))
    _post_event(
        client,
        {
            "id": "evt_checkout_done",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {"object": dict(account.checkouts[session_id])},
        },
    )

    assert back.json() == {"status": "paid", "amount_usd": 100.0}
    assert reloaded.json() == {"status": "paid", "amount_usd": 100.0}
    assert _lines(db, agency) == [(BalanceKind.top_up, Decimal("100.00"), invoice_id)]


@respx.mock
def test_a_payment_not_finished_or_not_this_agencys_adds_nothing(
    client: TestClient, db: Session
) -> None:
    user, agency, account = _paying(db)
    other_user, other_agency, _ = _paying(db, mock=False)
    unpaid = account.paid_checkout(10000)
    account.checkouts[unpaid]["payment_status"] = "unpaid"
    paid = account.paid_checkout(10000)

    waiting = client.post(
        f"{API}/agencies/{agency.id}/billing/top-up/confirm",
        json={"session_id": unpaid},
        cookies=_cookies(db, user),
    )
    stolen = client.post(
        f"{API}/agencies/{other_agency.id}/billing/top-up/confirm",
        json={"session_id": paid},
        cookies=_cookies(db, other_user),
    )

    assert waiting.json() == {"status": "processing", "amount_usd": None}
    assert stolen.status_code == 404
    assert _lines(db, agency) == []
    assert _lines(db, other_agency) == []


@respx.mock
def test_adding_funds_resumes_an_agency_that_ran_out(
    client: TestClient, db: Session
) -> None:
    user, agency, account = _paying(db)
    _use(db, user, "300.00")
    assert (
        billing_state.state_of(session=db, agency_id=agency.id).state is AgencyState.out
    )  # type: ignore[union-attr]
    invoice_id = account.invoice("top_up", 10000)

    _post_event(client, _invoice_event("invoice.paid", account, invoice_id))

    db.expire_all()
    money = billing_state.state_of(session=db, agency_id=agency.id)
    assert money is not None
    # $1 of the usage beyond the included amount came off what was added.
    assert (money.state, money.balance) == (AgencyState.active, Decimal("99.00"))


# ── Invoices on Billing ──


@respx.mock
def test_billing_lists_invoices_newest_first_with_what_they_were_for(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "SALES_CONTACT_URL", "https://meet.example.com/talk")
    user, agency, account = _paying(db)
    account.invoice("subscription", 29900)
    missed = account.invoice("top_up", 50000)
    account.invoice("auto_top_up", 20000, status="void")
    account.invoice("top_up", 10000, status="open")
    account.invoice("auto_top_up", 20000, status="draft")

    r = client.get(f"{API}/agencies/{agency.id}/billing", cookies=_cookies(db, user))

    assert r.status_code == 200, r.text
    body = r.json()
    assert [
        (i["description"], i["amount_usd"], i["status"]) for i in body["invoices"]
    ] == [
        ("Added funds", 100.0, "processing"),
        ("Auto top-up", 200.0, "failed"),
        ("Added funds", 500.0, "paid"),
        ("Subscription", 299.0, "paid"),
    ]
    assert body["invoices"][2]["url"] == f"https://invoice.stripe.com/i/{missed}"
    assert body["auto_top_up"] == {
        "enabled": False,
        "amount_usd": 200,
    }
    assert body["failed_payment"] is None
    assert body["sales_contact_url"] == "https://meet.example.com/talk"
    assert body["card"]["expires_soon"] is False
    # Opening Billing credits a paid top-up whose message never arrived.
    assert _lines(db, agency) == [(BalanceKind.top_up, Decimal("500.00"), missed)]


@respx.mock
def test_a_card_that_expires_this_month_is_flagged(
    client: TestClient, db: Session
) -> None:
    user, agency, account = _paying(db)
    today = datetime.now(UTC)
    assert account.card is not None
    account.card.update(exp_month=today.month, exp_year=today.year)

    r = client.get(f"{API}/agencies/{agency.id}/billing", cookies=_cookies(db, user))

    assert r.json()["card"]["expires_soon"] is True
    assert r.json()["sales_contact_url"] is None


# ── Auto top-up ──


def _auto(db: Session, agency: Agency, amount: int = 200) -> None:
    agency.auto_top_up_enabled = True
    agency.auto_top_up_amount_usd = amount
    db.add(agency)
    db.commit()


@pytest.mark.asyncio
@respx.mock
async def test_auto_top_up_charges_once_when_everything_is_used_up(
    db: Session, outbox: Outbox
) -> None:
    user, agency, account = _paying(db)
    _auto(db, agency)
    # With the included $299 untouched nothing is charged, whatever the balance.
    assert await top_up.run_auto_top_ups(session=db) == {"enough": 1}
    assert account.sent == []
    _use(db, user, "300.00")  # the included amount is gone and the balance is $0

    first = await top_up.run_auto_top_ups(session=db)
    second = await top_up.run_auto_top_ups(session=db)

    assert first == {"charged": 1}
    assert second == {"enough": 1}
    created = [s for s in account.sent if s.get("metadata[kind]") == "auto_top_up"]
    assert len(created) == 1
    assert created[0]["automatic_tax[enabled]"] == "true"
    assert [s["amount"] for s in account.sent if "amount" in s] == ["20000"]
    (kind, amount, invoice_id) = _lines(db, agency)[0]
    assert (kind, amount) == (BalanceKind.auto_top_up, Decimal("200.00"))
    assert account.calls == [f"finalize:{invoice_id}", f"pay:{invoice_id}"]
    assert outbox.sent == []


@pytest.mark.asyncio
@respx.mock
async def test_a_run_that_died_after_making_the_invoice_is_finished_not_repeated(
    db: Session, outbox: Outbox
) -> None:
    user, agency, account = _paying(db)
    _auto(db, agency)
    # What a run that stopped between making the invoice and charging it leaves.
    pending = account.invoice("auto_top_up", 20000, status="draft")
    agency.auto_top_up_invoice_id = pending
    db.add(agency)
    db.commit()

    outcome = await top_up.run_auto_top_ups(session=db)

    assert outcome == {"charged": 1}
    assert not [s for s in account.sent if s.get("metadata[kind]")]
    assert _lines(db, agency) == [(BalanceKind.auto_top_up, Decimal("200.00"), pending)]
    db.refresh(agency)
    assert agency.auto_top_up_invoice_id is None


@pytest.mark.asyncio
@respx.mock
async def test_two_runs_at_once_charge_the_card_once(
    db: Session, outbox: Outbox
) -> None:
    user, agency, account = _paying(db)
    _auto(db, agency)
    _use(db, user, "300.00")
    # Another run has just taken this agency's turn and not made its invoice yet.
    assert top_up._claim(db, agency) is not None

    while_claimed = await top_up.auto_top_up(session=db, agency=agency)

    assert while_claimed == "waiting"
    assert account.sent == [] and account.calls == []
    # A claim whose run died is taken over, and the card is then charged once.
    agency.auto_top_up_invoice_id = (
        f"claim:{int((datetime.now(UTC) - timedelta(minutes=11)).timestamp())}"
    )
    db.add(agency)
    db.commit()
    assert await top_up.auto_top_up(session=db, agency=agency) == "charged"
    assert len([s for s in account.sent if s.get("metadata[kind]")]) == 1
    # The $1 used beyond the included amount came off what was added.
    assert _balance(db, agency) == Decimal("199.00")


@pytest.mark.asyncio
@respx.mock
async def test_a_turn_with_enough_money_asks_stripe_nothing(db: Session) -> None:
    user, agency, account = _paying(db)
    billing_state.add_balance(
        session=db, agency=agency, amount_usd=Decimal("80"), note=None, created_by=None
    )
    _auto(db, agency)

    assert await top_up.auto_top_up(session=db, agency=agency) == "enough"
    assert not respx.calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer",
    [
        httpx.ConnectTimeout("timed out"),
        httpx.Response(200, content=b""),
        httpx.Response(200, content=b"<html>not json</html>"),
        httpx.Response(200, json={"id": "in_1", "status": "paid"}),
        httpx.Response(200, json={"id": "in_1", "subtotal": "a lot", "total": 1}),
    ],
)
@respx.mock
async def test_an_invoice_answer_that_cannot_be_used_raises_one_error(
    answer: Any,
) -> None:
    from app.services import stripe

    one = respx.get(f"{STRIPE}/invoices/in_1")
    many = respx.get(f"{STRIPE}/invoices")
    for route in (one, many):
        if isinstance(answer, Exception):
            route.mock(side_effect=answer)
        else:
            route.mock(return_value=answer)

    with pytest.raises(stripe.StripeError):
        await stripe.get_invoice(invoice_id="in_1")
    with pytest.raises(stripe.StripeError):
        await stripe.list_invoices(customer_id="cus_x")


@pytest.mark.asyncio
@respx.mock
async def test_a_declined_card_is_recorded_told_once_and_not_charged_again(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    user, agency, account = _paying(db)
    second_admin = _person(db)
    db.add(
        AgencyMember(
            agency_id=agency.id,
            user_id=second_admin.id,
            role=AgencyRole.admin,
            all_workspaces=True,
            can_approve=True,
        )
    )
    db.commit()
    _auto(db, agency)
    _use(db, user, "300.00")
    account.declines = True

    failed = await top_up.run_auto_top_ups(session=db)
    held = await top_up.run_auto_top_ups(session=db)

    assert (failed, held) == ({"failed": 1}, {"held": 1})
    # The invoice was voided, so Stripe cannot charge it later by itself.
    assert [c.split(":")[0] for c in account.calls] == ["finalize", "pay", "void"]
    assert _lines(db, agency) == []
    assert sorted(m["to"] for m in outbox.sent) == sorted(
        [user.email, second_admin.email]
    )
    assert set(outbox.subjects()) == {"A Connexity payment failed"}
    assert (
        "Your auto top-up of $200 failed: Your card was declined."
        in outbox.sent[0]["html"]
    )
    billing = client.get(
        f"{API}/agencies/{agency.id}/billing", cookies=_cookies(db, user)
    ).json()
    assert billing["failed_payment"]["amount_usd"] == 200
    assert billing["failed_payment"]["reason"] == "Your card was declined."
    status = client.get(
        f"{API}/agencies/{agency.id}/billing/status", cookies=_cookies(db, user)
    ).json()
    assert status["payment_failed"] is True

    # A new card: the failure is forgotten and the next run charges it.
    assert account.card is not None
    account.card.update(last4="1881")
    account.declines = False
    charged = await top_up.run_auto_top_ups(session=db)

    assert charged == {"charged": 1}
    assert len(outbox.sent) == 2
    db.refresh(agency)
    assert agency.payment_failed_at is None
    assert _balance(db, agency) == Decimal("199.00")


@pytest.mark.asyncio
@respx.mock
async def test_auto_top_up_does_nothing_when_off_or_when_there_is_enough(
    db: Session, outbox: Outbox
) -> None:
    user, agency, account = _paying(db)
    billing_state.add_balance(
        session=db, agency=agency, amount_usd=Decimal("80"), note=None, created_by=None
    )

    assert await top_up.run_auto_top_ups(session=db) == {}
    _auto(db, agency)
    assert await top_up.run_auto_top_ups(session=db) == {"enough": 1}

    assert account.sent == [] and account.calls == []


@respx.mock
def test_switching_auto_top_up_on_needs_a_card_and_sane_amounts(
    client: TestClient, db: Session
) -> None:
    user, agency, account = _paying(db)
    path = f"{API}/agencies/{agency.id}/billing/auto-top-up"
    cookies = _cookies(db, user)

    on = client.put(
        path,
        json={"enabled": True, "amount_usd": 500},
        cookies=cookies,
    )
    small_amount = client.put(
        path,
        json={"enabled": True, "amount_usd": 20},
        cookies=cookies,
    )
    account.card = None
    client.put(
        path,
        json={"enabled": False, "amount_usd": 500},
        cookies=cookies,
    )
    no_card = client.put(
        path,
        json={"enabled": True, "amount_usd": 500},
        cookies=cookies,
    )

    assert on.json() == {"enabled": True, "amount_usd": 500}
    assert small_amount.status_code == 422
    assert no_card.status_code == 409
    assert no_card.json()["detail"] == "Add a card first."
    db.refresh(agency)
    assert agency.auto_top_up_enabled is False


@pytest.mark.asyncio
@respx.mock
async def test_with_auto_top_up_on_running_out_does_not_pause_until_a_payment_fails(
    db: Session, outbox: Outbox
) -> None:
    user, agency, account = _paying(db)
    _use(db, user, "300.00")
    assert billing_state.records_calls(session=db, company_id=user.company_id) is False

    _auto(db, agency)
    db.expire_all()
    # In the minute before the card is charged, calls are still recorded.
    assert billing_state.records_calls(session=db, company_id=user.company_id) is True
    account.declines = True
    assert await top_up.auto_top_up(session=db, agency=agency) == "failed"

    db.expire_all()
    assert billing_state.records_calls(session=db, company_id=user.company_id) is False


# ── The emails ──


def test_the_low_and_paused_emails_go_out_once_per_stretch(
    db: Session, outbox: Outbox
) -> None:
    user, agency, _ = _paying(db)
    agency = _subscribe(db, agency, started_days_ago=4)
    _use(db, user, "279.00", days_ago=2.5)
    _use(db, user, "6.00", days_ago=1.5)
    _use(db, user, "6.00", days_ago=0.1)

    first = billing_notify.run_notifications(session=db)
    again = billing_notify.run_notifications(session=db)
    _use(db, user, "9.00", days_ago=0.05)  # all of it is used up
    paused = billing_notify.run_notifications(session=db)
    still = billing_notify.run_notifications(session=db)

    assert (first, again) == ({"low": 1}, {})
    assert (paused, still) == ({"paused": 1}, {})
    assert outbox.subjects() == ["Your Connexity balance is low", "Connexity is paused"]
    assert "You have $8.00 left." in outbox.sent[0]["html"]
    assert "Add funds and it resumes by itself." in outbox.sent[1]["html"]
    assert "https://app.example.com/agency/?section=billing" in outbox.sent[1]["html"]

    # Money arrives, and a later pause is told again.
    billing_state.add_balance(
        session=db, agency=agency, amount_usd=Decimal("500"), note=None, created_by=None
    )
    assert billing_notify.run_notifications(session=db) == {}
    db.refresh(agency)
    assert (agency.low_notified_at, agency.paused_notified_at) == (None, None)


def test_the_low_email_is_not_sent_while_auto_top_up_is_on(
    db: Session, outbox: Outbox
) -> None:
    user, agency, _ = _paying(db)
    agency = _subscribe(db, agency, started_days_ago=4)
    _auto(db, agency)
    _use(db, user, "279.00", days_ago=2.5)
    _use(db, user, "6.00", days_ago=1.5)
    _use(db, user, "6.00", days_ago=0.1)

    assert billing_notify.run_notifications(session=db) == {}
    assert outbox.sent == []


# ── Who, and the assistant ──


@respx.mock
def test_only_admins_add_funds_or_change_auto_top_up(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, agency, account = _paying(db)
    member = _person(db)
    db.add(
        AgencyMember(
            agency_id=agency.id,
            user_id=member.id,
            role=AgencyRole.member,
            all_workspaces=True,
            can_approve=True,
        )
    )
    db.commit()
    base = f"{API}/agencies/{agency.id}/billing"
    requests = [
        ("POST", f"{base}/top-up", {"amount_usd": 100}),
        ("POST", f"{base}/top-up/confirm", {"session_id": "cs_x"}),
        (
            "PUT",
            f"{base}/auto-top-up",
            {"enabled": False, "amount_usd": 200},
        ),
    ]

    for method, path, body in requests:
        assert (
            client.request(
                method, path, json=body, cookies=_cookies(db, member)
            ).status_code
            == 403
        )
        assert client.request(
            method, path, json=body, headers=_headers(user)
        ).status_code in (401, 403)
    assert account.sent == []
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", None)
    for method, path, body in requests:
        assert (
            client.request(
                method, path, json=body, cookies=_cookies(db, user)
            ).status_code
            == 404
        )


@respx.mock
def test_an_admins_assistant_reads_invoices_and_the_setting_and_changes_nothing(
    client: TestClient, db: Session
) -> None:
    user, agency, account = _paying(db)
    account.invoice("subscription", 29900)
    _auto(db, agency, amount=500)

    answer = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/usage",
        params={"agency": True},
        headers=_headers(user),
    ).json()

    assert answer["data"]["auto_top_up"] == {"enabled": True, "amount_usd": 500}
    assert [(i["description"], i["status"]) for i in answer["data"]["invoices"]] == [
        ("Subscription", "paid")
    ]
    assert any("never add funds" in rule for rule in answer["rules"])
    plain = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/usage", headers=_headers(user)
    ).json()
    assert plain["data"]["invoices"] is None and plain["data"]["auto_top_up"] is None
