"""What an agency has left, and the pause, through the API.

Paying is switched on for these tests with invented Stripe settings; no request leaves
the machine. The subscription's state is set directly, as Stripe's messages would.
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
import respx
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session, col, func, select

from app import crud
from app.core import encryption
from app.core.config import settings
from app.crud import billing as crud_billing
from app.models import Call, User
from app.models.agency import Agency, SubscriptionState
from app.models.agent import Agent
from app.models.billing import (
    AgencyState,
    BalanceEntry,
    BalanceKind,
    BillingPause,
    IncludedScan,
)
from app.models.company import Company
from app.models.enums import UsageMeter
from app.models.usage import UsageRecord
from app.services import billing_state, first_scan
from app.services.stripe import Subscription
from app.tests.api.routes.test_mcp_scan_calls import (
    ISSUER,
    MCP_URL,
    RetellAccount,
    _add,
    _call,
    _connect,
    _headers,
    _person,
    _scan,
    _scan_to_the_end,
    _stored,
)
from app.tests.api.routes.test_webhooks import _post as _post_webhook
from app.tests.utils.retell_payloads import retell_call

API = settings.API_V1_STR


@pytest.fixture(autouse=True)
def _paying_is_set_up(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_invented")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID", "price_invented")
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    monkeypatch.setattr(first_scan, "STEP_SECONDS", 0.0)
    monkeypatch.setattr(first_scan, "READ_PAGE", 50)
    yield
    encryption._fernet.cache_clear()


def _agency(db: Session, user: User) -> Agency:
    workspace = db.get(Company, user.company_id)
    assert workspace is not None
    agency = db.get(Agency, workspace.agency_id)
    assert agency is not None
    return agency


def _subscribe(
    db: Session,
    agency: Agency,
    state: SubscriptionState = SubscriptionState.active,
    *,
    started_days_ago: int = 10,
) -> Agency:
    start = datetime.now(UTC) - timedelta(days=started_days_ago)
    return crud_billing.store_subscription(
        session=db,
        agency=agency,
        subscription=Subscription(
            id="sub_invented",
            state=state,
            period_start=start,
            period_end=start + timedelta(days=30),
            ends_at_period_end=False,
            created=0,
        ),
    )


def _use(
    db: Session,
    user: User,
    dollars: str,
    *,
    days_ago: float = 1,
    agent: Agent | None = None,
) -> None:
    """Usage worth `dollars` at list price ($0.03 an observed minute), recorded
    `days_ago` days ago."""
    if agent is None:
        agent = db.exec(
            select(Agent).where(Agent.company_id == user.company_id)
        ).first()
    if agent is None:
        agent = Agent(company_id=user.company_id, name="Front desk")
        db.add(agent)
        db.flush()
    when = datetime.now(UTC) - timedelta(days=days_ago)
    db.add(
        UsageRecord(
            company_id=user.company_id,
            agent_id=agent.id,
            meter=UsageMeter.OBSERVED_MINUTES,
            quantity=int(Decimal(dollars) / Decimal("0.03")),
            occurred_at=when,
            source_key=f"call:{uuid.uuid4()}",
            created_at=when,
        )
    )
    db.commit()


def _money(db: Session, agency: Agency) -> billing_state.Money:
    db.expire_all()
    money = billing_state.state_of(session=db, agency_id=agency.id)
    assert money is not None
    return money


def _usage(client: TestClient, user: User) -> dict[str, Any]:
    r = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/usage", headers=_headers(user)
    )
    assert r.status_code == 200, r.text
    return r.json()


# ── The money ──


def test_usage_comes_off_the_included_amount_then_the_balance_which_stops_at_zero(
    db: Session,
) -> None:
    user = _person(db)
    agency = _subscribe(db, _agency(db, user))
    billing_state.add_balance(
        session=db,
        agency=agency,
        amount_usd=Decimal("50"),
        note="Added by Connexity",
        created_by=None,
    )

    _use(db, user, "120.00")
    below = _money(db, agency)
    _use(db, user, "210.00")  # $330 in all: $31 beyond the included $299
    above = _money(db, agency)
    again = _money(db, agency)
    _use(db, user, "90.00")  # $420 in all: $121 beyond, with $50 to draw from
    out = _money(db, agency)

    assert (below.state, below.included_left, below.balance) == (
        AgencyState.active,
        Decimal("179.00"),
        Decimal("50.00"),
    )
    assert (above.included_left, above.balance) == (Decimal("0.00"), Decimal("19.00"))
    assert (again.included_left, again.balance) == (above.included_left, above.balance)
    assert (out.state, out.balance) == (AgencyState.out, Decimal("0.00"))
    lines = db.exec(
        select(BalanceEntry).where(
            BalanceEntry.agency_id == agency.id,
            BalanceEntry.kind == BalanceKind.usage,
        )
    ).all()
    # One line for the period, rewritten each time, and never more than was there.
    assert [line.amount_usd for line in lines] == [Decimal("-50.00")]


def test_a_new_period_restores_the_included_amount_and_keeps_the_balance(
    db: Session,
) -> None:
    user = _person(db)
    agency = _subscribe(db, _agency(db, user), started_days_ago=31)
    billing_state.add_balance(
        session=db, agency=agency, amount_usd=Decimal("50"), note=None, created_by=None
    )
    _use(db, user, "321.00", days_ago=5)  # $22 beyond, in the old period
    assert _money(db, agency).balance == Decimal("28.00")
    # More usage arrives in the old period after it was last settled.
    _use(db, user, "9.00", days_ago=4)

    agency = _subscribe(db, agency, started_days_ago=1)
    renewed = _money(db, agency)

    assert renewed.state is AgencyState.active
    assert renewed.included_left == Decimal("299.00")
    assert renewed.balance == Decimal("19.00")


def test_what_was_recorded_before_the_subscription_is_never_charged(
    db: Session,
) -> None:
    user = _person(db)
    agency = _agency(db, user)
    _use(db, user, "400.00", days_ago=3)  # the first scan's calls

    agency = _subscribe(db, agency, started_days_ago=1)
    money = _money(db, agency)

    assert (money.state, money.included_left) == (
        AgencyState.active,
        Decimal("299.00"),
    )


# ── The states ──


def test_each_state_is_reached_and_left(db: Session) -> None:
    user = _person(db)
    agency = _agency(db, user)

    # No subscription, no agents yet: nothing to pause.
    assert _money(db, agency).state is AgencyState.first_scan

    agent = _add(db, user, _connect(db, user))
    assert _money(db, agency).state is AgencyState.first_scan
    workspace = db.get(Company, user.company_id)
    assert workspace is not None
    workspace.first_scan_done_at = datetime.now(UTC)
    db.add(workspace)
    db.commit()
    assert _money(db, agency).state is AgencyState.needs_subscription

    agency = _subscribe(db, agency)
    assert _money(db, agency).state is AgencyState.active
    agency = _subscribe(db, agency, SubscriptionState.past_due)
    assert _money(db, agency).state is AgencyState.active
    agency = _subscribe(db, agency, SubscriptionState.unpaid)
    assert _money(db, agency).state is AgencyState.unpaid
    agency = _subscribe(db, agency, SubscriptionState.ended)
    assert _money(db, agency).state is AgencyState.needs_subscription

    agency = _subscribe(db, agency)
    _use(db, user, "300.00", agent=agent)
    assert _money(db, agency).state is AgencyState.out
    billing_state.add_balance(
        session=db, agency=agency, amount_usd=Decimal("100"), note=None, created_by=None
    )
    assert _money(db, agency).state is AgencyState.active

    # Each pause was recorded and closed when it ended; none is open now.
    db.expire_all()
    pauses = db.exec(
        select(BillingPause)
        .where(BillingPause.agency_id == agency.id)
        .order_by(col(BillingPause.started_at))
    ).all()
    assert [p.reason for p in pauses] == [
        AgencyState.needs_subscription,
        AgencyState.unpaid,
        AgencyState.needs_subscription,
        AgencyState.out,
    ]
    assert all(p.ended_at is not None for p in pauses)


def test_low_means_less_than_a_week_left_and_only_with_enough_days_to_tell(
    db: Session,
) -> None:
    user = _person(db)
    agency = _subscribe(db, _agency(db, user), started_days_ago=4)

    # $279 used on one day: little left, and one day says nothing about a rate.
    _use(db, user, "279.00", days_ago=2.5)
    one_day = _money(db, agency)
    # Usage on three days, $291 in all: about $41 a day, with $8 left.
    _use(db, user, "6.00", days_ago=1.5)
    _use(db, user, "6.00", days_ago=0.1)
    three_days = _money(db, agency)

    assert (one_day.state, one_day.days_left) == (AgencyState.active, None)
    assert (three_days.state, three_days.days_left) == (AgencyState.low, 0)
    assert three_days.included_left == Decimal("8.00")


def test_it_is_not_low_when_the_next_period_comes_first(db: Session) -> None:
    user = _person(db)
    # The period ends tomorrow, and what is left lasts about two days.
    agency = _subscribe(db, _agency(db, user), started_days_ago=29)
    for days_ago in (2.5, 1.5, 0.1):
        _use(db, user, "69.00", days_ago=days_ago)

    money = _money(db, agency)

    assert money.days_left is not None and money.days_left < 7
    assert money.state is AgencyState.active


# ── The pause ──


def _paused_agency(db: Session) -> tuple[User, Agency, Agent, Any]:
    """An agency whose first scan is done and that has no subscription."""
    user = _person(db)
    integration = _connect(db, user)
    agent = _add(db, user, integration, platform_id=f"agent_{uuid.uuid4().hex[:8]}")
    workspace = db.get(Company, user.company_id)
    assert workspace is not None
    workspace.first_scan_done_at = datetime.now(UTC)
    db.add(workspace)
    db.commit()
    return user, _agency(db, user), agent, integration


def _calls(db: Session, agent: Agent) -> int:
    db.expire_all()
    return int(
        db.exec(select(func.count(col(Call.id))).where(Call.agent_id == agent.id)).one()
    )


def test_a_paused_agencys_calls_are_not_recorded_and_tests_cannot_run(
    client: TestClient, db: Session
) -> None:
    user, agency, agent, integration = _paused_agency(db)
    integration.encrypted_api_key = encryption.encrypt("key_invented_webhook_badge")
    db.add(integration)
    db.commit()
    payload = retell_call("call_while_paused", agent_id=agent.platform_agent_id)
    headers = _headers(user)
    base = f"{API}/mcp/workspaces/{user.company_id}"

    by_webhook = _post_webhook(
        client, integration.id, {"event": "call_ended", "call": payload}
    )
    scan = client.post(f"{base}/scan", headers=headers)
    add = client.post(
        f"{base}/agents",
        json={"agents": [{"platform_agent_id": "agent_x"}]},
        headers=headers,
    )
    run = client.post(
        f"{base}/agents/{agent.id}/test-runs", json={"all": True}, headers=headers
    )
    usage = _usage(client, user)
    status = client.get(
        f"{API}/agencies/{agency.id}/billing/status",
        cookies=_cookies(db, user),
    )

    # Retell is answered with success, so it does not send the call again.
    assert by_webhook.status_code == 200, by_webhook.text
    assert by_webhook.json()["reason"] == "paused"
    assert _calls(db, agent) == 0
    assert scan.status_code == add.status_code == 402
    assert "paused" in scan.json()["detail"]["error"]
    assert "Agency settings, Billing" in scan.json()["detail"]["next_steps"][0]
    assert run.status_code == 402
    assert run.json()["detail"]["error"] == (
        "Connexity is paused for this agency, so tests cannot run."
    )
    assert usage["data"]["money"]["state"] == "needs_subscription"
    assert any("paused" in step for step in usage["next_steps"])
    assert status.json()["state"] == "needs_subscription"
    # What is already there stays readable.
    assert client.get(f"{base}/agents", headers=headers).status_code == 200

    # A subscription resumes it by itself, and the call that came meanwhile is gone.
    _subscribe(db, agency)
    after = _post_webhook(
        client,
        integration.id,
        {
            "event": "call_ended",
            "call": retell_call("call_after", agent_id=agent.platform_agent_id),
        },
    )
    assert after.json()["status"] != "ignored"
    assert _calls(db, agent) == 1
    assert _usage(client, user)["data"]["money"]["state"] == "active"


def _cookies(db: Session, user: User) -> dict[str, str]:
    from app.core import security

    db.refresh(user)
    token, _ = security.create_session_token(
        user_id=user.id,
        company_id=user.company_id,
        session_version=user.session_version,
    )
    return {settings.AUTH_COOKIE: token}


@pytest.mark.asyncio
@respx.mock
async def test_the_pull_passes_over_a_paused_agencys_calls_for_good(
    db: Session,
) -> None:
    from app.models.call_pull import CallPullAccount
    from app.services import call_pull

    user, agency, agent, integration = _paused_agency(db)
    crud.fill_key_fingerprints(session=db)
    db.refresh(integration)
    assert agent.platform_agent_id
    account = RetellAccount(
        [
            retell_call(
                "call_missed",
                agent_id=agent.platform_agent_id,
                start_ms=int(
                    (datetime.now(UTC) - timedelta(minutes=30)).timestamp() * 1000
                ),
            )
        ]
    )
    account.mock()
    db.add(
        CallPullAccount(
            key_fingerprint=integration.key_fingerprint,
            cursor=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    db.commit()

    await call_pull.run_pull(session=db)
    assert _calls(db, agent) == 0

    # Running again, the same pull does not go back for it.
    _subscribe(db, agency)
    await call_pull.run_pull(session=db)

    assert _calls(db, agent) == 0
    assert account.read == []


def test_an_ingested_trace_is_refused_while_paused(
    client: TestClient, db: Session
) -> None:
    from app.tests.traces.examples import EXAMPLE_NAMES, load_example_json

    user, agency, agent, _ = _paused_agency(db)
    token = client.post(
        f"{API}/ingest-tokens/", json={"name": "traces"}, cookies=_cookies(db, user)
    )
    assert token.status_code == 200, token.text
    send = {
        "url": f"{API}/ingest/traces",
        "json": {
            "agent_id": str(agent.id),
            "trace": load_example_json(EXAMPLE_NAMES[0]),
        },
        "headers": {"Authorization": f"Bearer {token.json()['token']}"},
    }

    paused = client.post(**send)
    _subscribe(db, agency)
    running = client.post(**send)

    assert paused.status_code == 402
    assert "paused" in paused.json()["detail"]
    assert running.status_code == 200, running.text


def test_an_agency_that_only_sends_its_own_traces_is_asked_to_subscribe(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    agency = _agency(db, user)
    # No agent at all: nothing to pause yet.
    assert _money(db, agency).state is AgencyState.first_scan
    db.add(Agent(company_id=user.company_id, name="Self-hosted front desk"))
    db.commit()

    status = client.get(
        f"{API}/agencies/{agency.id}/billing/status", cookies=_cookies(db, user)
    )

    # There is no first scan to wait for, so the stripe can say what to do.
    assert status.json()["state"] == "needs_subscription"


def test_two_open_pause_records_do_not_break_the_agency(db: Session) -> None:
    user, agency, _agent, _integration = _paused_agency(db)
    assert _money(db, agency).state is AgencyState.needs_subscription
    # What two requests at the same moment can leave behind.
    db.add(BillingPause(agency_id=agency.id, reason=AgencyState.needs_subscription))
    db.commit()

    still = _money(db, agency)
    _subscribe(db, agency)
    running = _money(db, agency)

    assert still.state is AgencyState.needs_subscription
    assert running.state is AgencyState.active
    db.expire_all()
    open_now = db.exec(
        select(BillingPause).where(
            BillingPause.agency_id == agency.id,
            col(BillingPause.ended_at).is_(None),
        )
    ).all()
    assert open_now == []


def test_nothing_pauses_where_paying_is_not_set_up(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, agency, agent, integration = _paused_agency(db)
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", None)
    integration.encrypted_api_key = encryption.encrypt("key_invented_webhook_badge")
    db.add(integration)
    db.commit()

    stored = _post_webhook(
        client,
        integration.id,
        {
            "event": "call_ended",
            "call": retell_call("call_free", agent_id=agent.platform_agent_id),
        },
    )
    status = client.get(
        f"{API}/agencies/{agency.id}/billing/status", cookies=_cookies(db, user)
    )

    assert stored.json()["status"] != "ignored"
    assert _calls(db, agent) == 1
    assert status.status_code == 200
    assert status.json() is None
    assert _usage(client, user)["data"]["money"] is None


# ── The included first scan ──


@respx.mock
def test_the_included_first_scan_reads_the_latest_calls_up_to_its_limit(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(first_scan, "FIRST_SCAN_CALLS_PER_AGENT", 3)
    monkeypatch.setattr(first_scan, "FIRST_SCAN_CALLS_PER_AGENCY", 4)
    user = _person(db)
    integration = _connect(db, user)
    first = _add(db, user, integration, platform_id="agent_scan")
    second = _add(db, user, integration, platform_id="agent_two")
    RetellAccount(
        [
            *[_call(f"a_{i}", 24 * 20 - i) for i in range(5)],
            *[_call(f"b_{i}", 24 * 10 - i, agent_id="agent_two") for i in range(5)],
        ]
    ).mock()

    _scan_to_the_end(client, user)

    # The newest three of the first agent, then one: the agency's four are used up.
    assert _stored(db, first) == ["a_2", "a_3", "a_4"]
    assert _stored(db, second) == ["b_4"]
    db.refresh(first)
    db.refresh(second)
    assert (first.scan_total, first.scan_window_total) == (3, 5)
    assert (second.scan_total, second.scan_window_total) == (1, 5)
    usage = _usage(client, user)
    assert usage["data"]["money"]["state"] == "needs_subscription"
    assert usage["data"]["money"]["first_scan"] == {"checked": 4, "of": 10}


@respx.mock
def test_a_subscribed_agencys_scan_has_no_limit(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(first_scan, "FIRST_SCAN_CALLS_PER_AGENT", 3)
    user = _person(db)
    _subscribe(db, _agency(db, user))
    agent = _add(db, user, _connect(db, user))
    RetellAccount([_call(f"a_{i}", 24 * 20 - i) for i in range(5)]).mock()

    _scan_to_the_end(client, user)

    assert len(_stored(db, agent)) == 5
    db.refresh(agent)
    assert agent.scan_window_total is None


@respx.mock
def test_one_included_scan_per_voice_platform_account(
    client: TestClient, db: Session
) -> None:
    fingerprint = uuid.uuid4().hex
    earlier, later = _person(db), _person(db)
    agents = []
    for user in (earlier, later):
        integration = _connect(db, user)
        integration.key_fingerprint = fingerprint
        db.add(integration)
        db.commit()
        agents.append(_add(db, user, integration))
    RetellAccount([_call(f"a_{i}", 24 * 20 - i) for i in range(3)]).mock()

    _scan_to_the_end(client, earlier)
    _scan_to_the_end(client, later)

    assert len(_stored(db, agents[0])) == 3
    assert _stored(db, agents[1]) == []
    used = db.get(IncludedScan, fingerprint)
    assert used is not None
    assert used.agency_id == _agency(db, earlier).id
    assert _scan(client, later).status_code == 402
