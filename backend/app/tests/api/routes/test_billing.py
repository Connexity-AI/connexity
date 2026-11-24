"""The agency's subscription, through the API, with Stripe faked.

No request leaves the machine: every call to Stripe is answered by `respx`. Customers,
subscriptions and cards are invented.
"""

import hashlib
import hmac
import json
import time
import uuid
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.models import User, UserCreate
from app.models.agency import Agency, AgencyMember, AgencyRole, SubscriptionState
from app.models.billing import StripeEvent
from app.models.company import Company
from app.services import stripe
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
STRIPE = "https://api.stripe.com/v1"
SECRET = "whsec_test_secret"
PERIOD_START = 1795996800  # 30 Nov 2026, 00:00 UTC
PERIOD_END = 1798675200  # 31 Dec 2026, 00:00 UTC


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_invented")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID", "price_invented")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(settings, "STRIPE_AUTOMATIC_TAX", True)
    monkeypatch.setattr(settings, "SITE_URL", "https://app.example.com")
    monkeypatch.setattr(
        settings, "OAUTH_DEFAULT_RESOURCE_URL", "https://mcp.example.com/mcp"
    )
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")


def _person(db: Session, name: str | None = None) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=random_lower_string(), full_name=name
        ),
    )


def _web(db: Session, user: User) -> dict[str, str]:
    db.refresh(user)
    token, _ = security.create_session_token(
        user_id=user.id,
        company_id=user.company_id,
        session_version=user.session_version,
    )
    return {settings.AUTH_COOKIE: token}


def _assistant(db: Session, user: User) -> dict[str, str]:
    _, token = crud.create_personal_access_token(
        session=db, user_id=user.id, name="Claude Code"
    )
    return {"Authorization": f"Bearer {token}"}


def _agency_of(db: Session, user: User) -> Agency:
    workspace = db.get(Company, user.company_id)
    assert workspace is not None
    agency = db.get(Agency, workspace.agency_id)
    assert agency is not None
    return agency


def _with_customer(db: Session, agency: Agency) -> str:
    customer_id = f"cus_{uuid.uuid4().hex[:12]}"
    agency.stripe_customer_id = customer_id
    db.add(agency)
    db.commit()
    return customer_id


def _subscription(status: str = "active", **more: Any) -> dict[str, Any]:
    """A subscription as Stripe answers it in the version this code is written for:
    the period sits on the item."""
    return {
        "id": "sub_invented",
        "object": "subscription",
        "status": status,
        "created": 1795996800,
        "cancel_at_period_end": False,
        "cancel_at": None,
        "items": {
            "data": [
                {
                    "current_period_start": PERIOD_START,
                    "current_period_end": PERIOD_END,
                }
            ]
        },
        **more,
    }


def _listing(*subscriptions: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json={"object": "list", "data": list(subscriptions)})


def _signed(body: dict[str, Any], *, secret: str = SECRET, at: int | None = None):
    raw = json.dumps(body).encode()
    timestamp = str(int(time.time()) if at is None else at)
    digest = hmac.new(
        secret.encode(), timestamp.encode() + b"." + raw, hashlib.sha256
    ).hexdigest()
    return raw, {
        "stripe-signature": f"t={timestamp},v1={digest}",
        "content-type": "application/json",
    }


def _event(customer_id: str, *, status: str = "active", event_id: str | None = None):
    return {
        "id": event_id or f"evt_{uuid.uuid4().hex[:16]}",
        "object": "event",
        "type": "customer.subscription.updated",
        "data": {"object": {**_subscription(status), "customer": customer_id}},
    }


def _post_event(client: TestClient, body: dict[str, Any], **signing: Any):
    raw, headers = _signed(body, **signing)
    return client.post(f"{API}/webhooks/stripe", content=raw, headers=headers)


def _form(request: httpx.Request) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


# ── Starting ──


@respx.mock
def test_starting_makes_one_customer_and_a_checkout_for_the_one_price(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    made = respx.post(f"{STRIPE}/customers").mock(
        return_value=httpx.Response(200, json={"id": "cus_new_one"})
    )
    respx.get(f"{STRIPE}/subscriptions").mock(return_value=_listing())
    # The second start finds the first one's page still open, and closes it.
    respx.get(f"{STRIPE}/checkout/sessions").mock(
        side_effect=[
            httpx.Response(200, json={"data": []}),
            httpx.Response(200, json={"data": [{"id": "cs_1", "status": "open"}]}),
        ]
    )
    expired = respx.post(f"{STRIPE}/checkout/sessions/cs_1/expire").mock(
        return_value=httpx.Response(200, json={"id": "cs_1", "status": "expired"})
    )
    checkout = respx.post(f"{STRIPE}/checkout/sessions").mock(
        return_value=httpx.Response(
            200, json={"id": "cs_1", "url": "https://checkout.stripe.com/c/pay/cs_1"}
        )
    )
    path = f"{API}/agencies/{agency.id}/billing/checkout"

    first = client.post(path, cookies=_web(db, admin))
    second = client.post(path, cookies=_web(db, admin))

    assert first.status_code == 200, first.text
    assert first.json() == {"url": "https://checkout.stripe.com/c/pay/cs_1"}
    assert second.status_code == 200
    assert made.call_count == 1
    assert expired.call_count == 1
    assert checkout.call_count == 2
    sent_customer = _form(made.calls[0].request)
    assert sent_customer == {"name": agency.name, "metadata[agency_id]": str(agency.id)}
    sent = _form(checkout.calls[0].request)
    assert sent["mode"] == "subscription"
    assert sent["customer"] == "cus_new_one"
    assert sent["line_items[0][price]"] == "price_invented"
    assert sent["automatic_tax[enabled]"] == "true"
    assert sent["tax_id_collection[enabled]"] == "true"
    assert sent["billing_address_collection"] == "required"
    assert sent["success_url"] == (
        "https://app.example.com/agency/?section=billing&checkout=done"
    )
    assert sent["cancel_url"] == "https://app.example.com/agency/?section=billing"
    assert checkout.calls[0].request.headers["stripe-version"] == "2025-09-30.clover"
    db.refresh(agency)
    assert agency.stripe_customer_id == "cus_new_one"
    assert agency.subscription_state is SubscriptionState.none


@respx.mock
def test_an_agency_with_a_subscription_cannot_start_another(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    _with_customer(db, agency)
    respx.get(f"{STRIPE}/subscriptions").mock(return_value=_listing(_subscription()))
    checkout = respx.post(f"{STRIPE}/checkout/sessions")

    refused = client.post(
        f"{API}/agencies/{agency.id}/billing/checkout", cookies=_web(db, admin)
    )

    assert refused.status_code == 409
    assert not checkout.called


# ── Stripe's messages ──


@respx.mock
def test_a_message_sets_the_subscription_and_a_repeat_does_nothing(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    customer_id = _with_customer(db, agency)
    listing = respx.get(f"{STRIPE}/subscriptions").mock(
        return_value=_listing(_subscription())
    )
    event = _event(customer_id)

    first = _post_event(client, event)
    again = _post_event(client, event)

    assert first.status_code == 200, first.text
    assert first.json()["status"] == "stored"
    assert again.json() == {
        "status": "ignored",
        "reason": "already handled",
        "call_id": None,
        "call_ids": [],
    }
    assert listing.call_count == 1
    assert _form_params(listing.calls[0].request) == {
        "customer": customer_id,
        "status": "all",
        "limit": "20",
    }
    db.refresh(agency)
    assert agency.subscription_state is SubscriptionState.active
    assert agency.stripe_subscription_id == "sub_invented"
    assert agency.subscription_period_end is not None
    assert int(agency.subscription_period_end.timestamp()) == PERIOD_END
    assert agency.subscription_ends_at_period_end is False


def _form_params(request: httpx.Request) -> dict[str, str]:
    return dict(request.url.params)


@respx.mock
def test_a_late_older_message_does_not_move_the_state_back(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    customer_id = _with_customer(db, agency)
    # Whatever a message says, Stripe is asked, and Stripe says it is active.
    respx.get(f"{STRIPE}/subscriptions").mock(return_value=_listing(_subscription()))

    _post_event(client, _event(customer_id, status="active"))
    late = _post_event(client, _event(customer_id, status="incomplete"))

    assert late.status_code == 200
    db.refresh(agency)
    assert agency.subscription_state is SubscriptionState.active


@pytest.mark.parametrize(
    ("status", "more", "state", "ends"),
    [
        ("past_due", {}, SubscriptionState.past_due, False),
        ("unpaid", {}, SubscriptionState.unpaid, False),
        ("canceled", {"cancel_at_period_end": True}, SubscriptionState.ended, False),
        ("active", {"cancel_at_period_end": True}, SubscriptionState.active, True),
        ("active", {"cancel_at": PERIOD_END}, SubscriptionState.active, True),
        ("incomplete", {}, SubscriptionState.none, False),
    ],
)
@respx.mock
def test_each_state_stripe_reports_becomes_connexitys(
    client: TestClient,
    db: Session,
    status: str,
    more: dict[str, Any],
    state: SubscriptionState,
    ends: bool,
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    customer_id = _with_customer(db, agency)
    respx.get(f"{STRIPE}/subscriptions").mock(
        return_value=_listing(_subscription(status, **more))
    )

    assert _post_event(client, _event(customer_id)).status_code == 200

    db.refresh(agency)
    assert agency.subscription_state is state
    assert agency.subscription_ends_at_period_end is ends


@respx.mock
def test_a_running_subscription_wins_over_one_that_ended(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    customer_id = _with_customer(db, agency)
    old = _subscription("canceled", id="sub_old", created=1700000000)
    new = _subscription("active", id="sub_new", created=1795996800)
    respx.get(f"{STRIPE}/subscriptions").mock(return_value=_listing(old, new))

    _post_event(client, _event(customer_id))

    db.refresh(agency)
    assert agency.stripe_subscription_id == "sub_new"
    assert agency.subscription_state is SubscriptionState.active


@respx.mock
def test_an_unfinished_attempt_does_not_hide_a_paid_subscription(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    customer_id = _with_customer(db, agency)
    paid = _subscription("active", id="sub_paid", created=1700000000)
    unfinished = _subscription("incomplete", id="sub_unfinished", created=1795996800)
    respx.get(f"{STRIPE}/subscriptions").mock(return_value=_listing(paid, unfinished))

    _post_event(client, _event(customer_id))

    db.refresh(agency)
    assert agency.stripe_subscription_id == "sub_paid"
    assert agency.subscription_state is SubscriptionState.active


@respx.mock
def test_a_message_that_cannot_be_trusted_or_placed_changes_nothing(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    customer_id = _with_customer(db, agency)
    listing = respx.get(f"{STRIPE}/subscriptions").mock(
        return_value=_listing(_subscription())
    )
    event = _event(customer_id)

    wrong_secret = _post_event(client, event, secret="whsec_someone_else")
    too_old = _post_event(client, event, at=int(time.time()) - 3600)
    raw, _ = _signed(event)
    unsigned = client.post(f"{API}/webhooks/stripe", content=raw)
    stranger = _post_event(client, _event("cus_nobody_here"))

    assert wrong_secret.status_code == too_old.status_code == 401
    assert unsigned.status_code == 401
    assert stranger.status_code == 200
    assert stranger.json()["reason"] == "not about a known customer"
    assert not listing.called
    db.refresh(agency)
    assert agency.subscription_state is SubscriptionState.none


@respx.mock
def test_when_stripe_cannot_be_read_the_message_is_asked_for_again(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    customer_id = _with_customer(db, agency)
    listing = respx.get(f"{STRIPE}/subscriptions").mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )
    event = _event(customer_id)

    failed = _post_event(client, event)

    assert failed.status_code == 503
    assert db.get(StripeEvent, event["id"]) is None
    listing.mock(return_value=_listing(_subscription()), side_effect=None)
    assert _post_event(client, event).json()["status"] == "stored"
    db.refresh(agency)
    assert agency.subscription_state is SubscriptionState.active


# ── Billing, cancel and resume ──


def _customer_answer() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "cus_x",
            "name": "Signal Voice Inc.",
            "address": {
                "line1": "1 Example Street",
                "line2": None,
                "city": "Ottawa",
                "state": "ON",
                "postal_code": "K1A 0A1",
                "country": "CA",
            },
            "invoice_settings": {
                "default_payment_method": {
                    "id": "pm_1",
                    "card": {
                        "brand": "visa",
                        "last4": "4242",
                        "exp_month": 8,
                        "exp_year": 2028,
                    },
                }
            },
            "tax_ids": {"data": [{"type": "ca_gst_hst", "value": "123456789RT0001"}]},
        },
    )


@respx.mock
def test_billing_reads_the_subscription_card_and_details_from_stripe(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    customer_id = _with_customer(db, agency)
    respx.get(f"{STRIPE}/subscriptions").mock(return_value=_listing(_subscription()))
    respx.get(f"{STRIPE}/customers/{customer_id}").mock(return_value=_customer_answer())

    r = client.get(f"{API}/agencies/{agency.id}/billing", cookies=_web(db, admin))

    assert r.status_code == 200, r.text
    assert r.json() == {
        "subscription": {
            "state": "active",
            "price_usd": 299,
            "included_usd": 299,
            "period_end": "2026-12-31T00:00:00Z",
            "ends_at_period_end": False,
        },
        "card": {"brand": "visa", "last4": "4242", "exp_month": 8, "exp_year": 2028},
        "details": {
            "name": "Signal Voice Inc.",
            "address": ["1 Example Street", "Ottawa ON K1A 0A1", "CA"],
            "tax_ids": ["123456789RT0001"],
        },
        "read_from_stripe": True,
    }


@respx.mock
def test_billing_shows_the_last_known_state_when_stripe_is_down(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    _with_customer(db, agency)
    agency.subscription_state = SubscriptionState.active
    db.add(agency)
    db.commit()
    respx.get(f"{STRIPE}/subscriptions").mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )

    r = client.get(f"{API}/agencies/{agency.id}/billing", cookies=_web(db, admin))

    assert r.status_code == 200
    assert r.json()["subscription"]["state"] == "active"
    assert (r.json()["card"], r.json()["details"]) == (None, None)
    assert r.json()["read_from_stripe"] is False


@respx.mock
def test_before_any_payment_billing_asks_stripe_nothing(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)

    r = client.get(f"{API}/agencies/{agency.id}/billing", cookies=_web(db, admin))

    assert r.status_code == 200
    assert r.json()["subscription"]["state"] == "none"
    assert r.json()["card"] is None
    assert not respx.calls


@respx.mock
def test_cancel_runs_to_the_end_of_the_period_and_resume_undoes_it(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    _with_customer(db, agency)
    respx.get(f"{STRIPE}/subscriptions").mock(return_value=_listing(_subscription()))
    change = respx.post(f"{STRIPE}/subscriptions/sub_invented").mock(
        side_effect=lambda request: httpx.Response(
            200,
            json=_subscription(
                cancel_at_period_end=_form(request)["cancel_at_period_end"] == "true"
            ),
        )
    )
    base = f"{API}/agencies/{agency.id}/billing"

    cancelled = client.post(f"{base}/cancel", cookies=_web(db, admin))
    db.refresh(agency)
    ends_after_cancel = agency.subscription_ends_at_period_end
    resumed = client.post(f"{base}/resume", cookies=_web(db, admin))

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["subscription"]["ends_at_period_end"] is True
    assert cancelled.json()["subscription"]["state"] == "active"
    assert ends_after_cancel is True
    assert resumed.json()["subscription"]["ends_at_period_end"] is False
    assert [_form(c.request) for c in change.calls] == [
        {"cancel_at_period_end": "true"},
        {"cancel_at_period_end": "false"},
    ]


@respx.mock
def test_the_portal_link_needs_a_customer_and_stripe(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    path = f"{API}/agencies/{agency.id}/billing/portal"

    before = client.post(path, cookies=_web(db, admin))
    customer_id = _with_customer(db, agency)
    portal = respx.post(f"{STRIPE}/billing_portal/sessions").mock(
        return_value=httpx.Response(
            200, json={"url": "https://billing.stripe.com/p/session/x"}
        )
    )
    opened = client.post(path, cookies=_web(db, admin))
    portal.mock(return_value=httpx.Response(500, json={"error": {"message": "boom"}}))
    down = client.post(path, cookies=_web(db, admin))

    assert before.status_code == 409
    assert opened.json() == {"url": "https://billing.stripe.com/p/session/x"}
    assert _form(portal.calls[0].request) == {
        "customer": customer_id,
        "return_url": "https://app.example.com/agency/?section=billing",
    }
    assert down.status_code == 502
    assert down.json()["detail"] == (
        "The payment provider could not be reached. Try again in a minute."
    )


# ── Who ──


@respx.mock
def test_only_admins_reach_billing(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin, member, outsider = _person(db, "Alex Morgan"), _person(db), _person(db)
    agency = _agency_of(db, admin)
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
    routes = [
        ("GET", base),
        ("POST", f"{base}/checkout"),
        ("POST", f"{base}/portal"),
        ("POST", f"{base}/cancel"),
        ("POST", f"{base}/resume"),
    ]

    for method, path in routes:
        by_member = client.request(method, path, cookies=_web(db, member))
        assert by_member.status_code == 403, path
        assert by_member.json()["detail"] == (
            "Only Admins can see billing. Ask Alex Morgan."
        )
        assert (
            client.request(method, path, cookies=_web(db, outsider)).status_code == 404
        )
        assert client.request(method, path).status_code == 401
    assert not respx.calls

    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", None)
    for method, path in routes:
        assert client.request(method, path, cookies=_web(db, admin)).status_code == 404
    raw, headers = _signed(_event("cus_any"))
    assert (
        client.post(f"{API}/webhooks/stripe", content=raw, headers=headers).status_code
        == 404
    )


def test_an_assistant_reads_the_subscription_and_is_told_it_changes_nothing(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    agency.subscription_state = SubscriptionState.past_due
    db.add(agency)
    db.commit()
    path = f"{API}/mcp/workspaces/{admin.company_id}/usage"
    headers = _assistant(db, admin)

    answer = client.get(path, headers=headers).json()

    assert answer["data"]["subscription"] == {
        "state": "past_due",
        "price_usd": 299,
        "included_usd": 299,
        "period_end": None,
        "ends_at_period_end": False,
    }
    assert any("never start, pay, cancel" in rule for rule in answer["rules"])
    assert any("renewal payment failed" in step for step in answer["next_steps"])
    # No tool reaches the billing routes: they take a web session only.
    assert client.post(
        f"{API}/agencies/{agency.id}/billing/cancel", headers=headers
    ).status_code in (401, 403)
    # Where paying is not set up, the answer says nothing about a subscription.
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID", None)
    assert client.get(path, headers=headers).json()["data"]["subscription"] is None


# ── Stripe itself: a timeout, an empty answer, a malformed one ──


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer",
    [
        httpx.ConnectTimeout("timed out"),
        httpx.Response(200, content=b""),
        httpx.Response(200, content=b"<html>not json</html>"),
        httpx.Response(200, json=["a", "list"]),
        httpx.Response(200, json={"object": "list"}),
        httpx.Response(200, json={"data": [{"id": "sub_1", "status": "brand_new"}]}),
        httpx.Response(402, json={"error": {"message": "Your card was declined."}}),
    ],
)
@respx.mock
async def test_stripe_answers_that_cannot_be_used_raise_one_error(answer: Any) -> None:
    route = respx.get(f"{STRIPE}/subscriptions")
    if isinstance(answer, Exception):
        route.mock(side_effect=answer)
    else:
        route.mock(return_value=answer)

    with pytest.raises(stripe.StripeError):
        await stripe.current_subscription(customer_id="cus_x")


@pytest.mark.asyncio
@respx.mock
async def test_a_checkout_answer_without_an_address_is_an_error() -> None:
    respx.post(f"{STRIPE}/checkout/sessions").mock(
        return_value=httpx.Response(200, json={"id": "cs_1"})
    )

    with pytest.raises(stripe.StripeError):
        await stripe.create_checkout(
            customer_id="cus_x", success_url="https://a", cancel_url="https://b"
        )


def test_the_older_place_for_a_subscriptions_period_is_read_too() -> None:
    old_shape = {
        "id": "sub_1",
        "status": "active",
        "created": 1,
        "current_period_start": PERIOD_START,
        "current_period_end": PERIOD_END,
        "items": {"data": [{"id": "si_1"}]},
    }

    found = stripe.read_subscription(old_shape)

    assert found.period_end is not None
    assert int(found.period_end.timestamp()) == PERIOD_END
