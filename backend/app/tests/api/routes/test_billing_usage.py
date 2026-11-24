"""An agency's usage on Billing, through the API. Paying is switched on with invented
settings; nothing leaves the machine."""

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import User
from app.models.agency import AgencyMember, AgencyRole
from app.models.agent import Agent
from app.models.company import Company
from app.models.enums import UsageMeter
from app.models.usage import UsageRecord
from app.services import billing_state
from app.tests.api.routes.test_balance_and_pause import (
    _agency,
    _cookies,
    _subscribe,
)
from app.tests.api.routes.test_mcp_scan_calls import (
    ISSUER,
    MCP_URL,
    _headers,
    _person,
)

API = settings.API_V1_STR


@pytest.fixture(autouse=True)
def _paying_is_set_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_invented")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID", "price_invented")
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)


def _agent(db: Session, company_id: uuid.UUID, name: str) -> Agent:
    agent = Agent(company_id=company_id, name=name)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _record(
    db: Session,
    agent: Agent,
    meter: UsageMeter,
    quantity: int,
    *,
    days_ago: float = 1,
    run_id: uuid.UUID | None = None,
) -> None:
    when = datetime.now(UTC) - timedelta(days=days_ago)
    db.add(
        UsageRecord(
            company_id=agent.company_id,
            agent_id=agent.id,
            meter=meter,
            quantity=quantity,
            occurred_at=when,
            source_key=f"x:{uuid.uuid4()}",
            created_at=when,
            own_cost_usd=1.23,
            model="claude-secret-model",
        )
    )
    db.commit()


def _second_workspace(
    client: TestClient, db: Session, admin: User, name: str
) -> Company:
    r = client.post(
        f"{API}/workspaces/", json={"name": name}, cookies=_cookies(db, admin)
    )
    assert r.status_code == 200, r.text
    workspace = db.get(Company, uuid.UUID(r.json()["id"]))
    assert workspace is not None
    return workspace


def _an_agency_with_usage(client: TestClient, db: Session):
    admin = _person(db)
    agency = _subscribe(db, _agency(db, admin), started_days_ago=10)
    first = db.get(Company, admin.company_id)
    assert first is not None
    first.name = "Northfield Group"
    db.add(first)
    db.commit()
    bright = _second_workspace(client, db, admin, "Bright Dental")
    booking = _agent(db, first.id, "Car service booking")
    renewals = _agent(db, first.id, "Insurance renewals")
    reception = _agent(db, bright.id, "Dental reception")
    _record(db, booking, UsageMeter.OBSERVED_MINUTES, 100)  # $3.00
    _record(db, renewals, UsageMeter.SIMULATED_CALLER_MESSAGES, 50)  # $1.00
    _record(db, reception, UsageMeter.OBSERVED_MINUTES, 620)  # $18.60
    _record(db, reception, UsageMeter.SIMULATED_CALLER_MESSAGES, 486)  # $9.72
    # Before the period began, and so in "last period" only.
    _record(db, booking, UsageMeter.OBSERVED_MINUTES, 1000, days_ago=20)
    return admin, agency, first, bright


def test_this_period_adds_up_per_workspace_and_agent_and_equals_what_was_drawn(
    client: TestClient, db: Session
) -> None:
    admin, agency, first, bright = _an_agency_with_usage(client, db)

    r = client.get(
        f"{API}/agencies/{agency.id}/billing/usage", cookies=_cookies(db, admin)
    )

    assert r.status_code == 200, r.text
    usage = r.json()
    assert usage["period"]["key"] == "this"
    assert [p["label"] for p in usage["periods"]] == [
        "This period",
        "Last period",
        "Last 30 days",
    ]
    assert usage["cost_usd"] == 32.32
    assert [
        (p["label"], p["quantity"], p["unit"], p["cost_usd"]) for p in usage["parts"]
    ] == [
        ("Calls observed", 720, "min", 21.6),
        ("Text simulations", 536, "messages", 10.72),
    ]
    assert [
        (w["name"], w["observed_minutes"], w["simulated_messages"], w["cost_usd"])
        for w in usage["workspaces"]
    ] == [("Bright Dental", 620, 486, 28.32), ("Northfield Group", 100, 50, 4.0)]
    assert [(a["name"], a["cost_usd"]) for a in usage["workspaces"][1]["agents"]] == [
        ("Car service booking", 3.0),
        ("Insurance renewals", 1.0),
    ]
    # The parts, the workspaces and their agents all come to the same total.
    assert round(sum(p["cost_usd"] for p in usage["parts"]), 2) == usage["cost_usd"]
    assert (
        round(sum(w["cost_usd"] for w in usage["workspaces"]), 2) == usage["cost_usd"]
    )
    for workspace in usage["workspaces"]:
        assert (
            round(sum(a["cost_usd"] for a in workspace["agents"]), 2)
            == (workspace["cost_usd"])
        )
    assert usage["movers"][0] == {
        "label": b"Bright Dental\\u2019s calls".decode("unicode_escape"),
        "quantity": 620,
        "unit": "min",
        "cost_usd": 18.6,
    }
    # It is exactly what came off the included amount.
    db.expire_all()
    money = billing_state.state_of(session=db, agency_id=agency.id)
    assert money is not None
    assert money.included_left == Decimal("299") - Decimal(str(usage["cost_usd"]))
    # Connexity's own costs are nowhere in the answer.
    assert "own_cost" not in r.text and "claude-secret-model" not in r.text


def test_the_other_periods_and_an_agency_without_a_subscription(
    client: TestClient, db: Session
) -> None:
    admin, agency, _first, _bright = _an_agency_with_usage(client, db)
    base = f"{API}/agencies/{agency.id}/billing/usage"

    last = client.get(
        base, params={"period": "last"}, cookies=_cookies(db, admin)
    ).json()
    thirty = client.get(
        base, params={"period": "30d"}, cookies=_cookies(db, admin)
    ).json()
    someone = _person(db)
    theirs = _agency(db, someone)
    alone = client.get(
        f"{API}/agencies/{theirs.id}/billing/usage",
        params={"period": "this"},
        cookies=_cookies(db, someone),
    ).json()

    assert (last["period"]["key"], last["cost_usd"]) == ("last", 30.0)
    assert last["period"]["ends_at"] == last["periods"][0]["starts_at"]
    assert thirty["cost_usd"] == 62.32
    # No subscription: only the last 30 days exist, whatever was asked for.
    assert [p["key"] for p in alone["periods"]] == ["30d"]
    assert alone["period"]["key"] == "30d"
    assert (alone["cost_usd"], alone["workspaces"], alone["movers"]) == (0.0, [], [])
    assert [p["quantity"] for p in alone["parts"]] == [0, 0]


def test_a_deleted_workspaces_usage_stays_under_its_name(
    client: TestClient, db: Session
) -> None:
    admin, agency, _first, bright = _an_agency_with_usage(client, db)
    deleted = client.post(
        f"{API}/agencies/{agency.id}/workspaces/{bright.id}/deletion",
        json={"name": "Bright Dental"},
        cookies=_cookies(db, admin),
    )
    assert deleted.status_code == 200, deleted.text

    usage = client.get(
        f"{API}/agencies/{agency.id}/billing/usage", cookies=_cookies(db, admin)
    ).json()

    kept = next(w for w in usage["workspaces"] if w["name"] == "Bright Dental")
    assert (kept["deleted"], kept["cost_usd"]) == (True, 28.32)
    assert [a["name"] for a in kept["agents"]] == ["Dental reception"]
    assert usage["cost_usd"] == 32.32


def test_the_csv_has_one_row_per_workspace_and_agent_and_the_same_total(
    client: TestClient, db: Session
) -> None:
    admin, agency, first, _bright = _an_agency_with_usage(client, db)
    risky = _agent(db, first.id, "=SUM(A1)")
    _record(db, risky, UsageMeter.OBSERVED_MINUTES, 1)

    r = client.get(
        f"{API}/agencies/{agency.id}/billing/usage.csv", cookies=_cookies(db, admin)
    )

    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == [
        "Workspace",
        "Agent",
        "Calls observed (min)",
        "Simulated messages",
        "Cost (USD)",
    ]
    assert rows[1] == ["Bright Dental", "Dental reception", "620", "486", "28.32"]
    assert ["Northfield Group", "Car service booking", "100", "0", "3.00"] in rows
    # A name that starts like a formula is not one a spreadsheet will run.
    assert ["Northfield Group", "'=SUM(A1)", "1", "0", "0.03"] in rows
    assert rows[-1] == ["Total", "", "721", "536", "32.35"]


def test_only_admins_see_usage_on_the_web_and_through_an_assistant(
    client: TestClient, db: Session
) -> None:
    admin, agency, first, _bright = _an_agency_with_usage(client, db)
    member, outsider = _person(db), _person(db)
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
    from app.models.workspace_member import WorkspaceMember

    db.add(WorkspaceMember(user_id=member.id, company_id=first.id))
    db.commit()
    for path in ("usage", "usage.csv"):
        url = f"{API}/agencies/{agency.id}/billing/{path}"
        assert client.get(url, cookies=_cookies(db, member)).status_code == 403
        assert client.get(url, cookies=_cookies(db, outsider)).status_code == 404
        assert client.get(url, headers=_headers(admin)).status_code in (401, 403)
    tool = f"{API}/mcp/workspaces/{first.id}/usage"

    for_admin = client.get(tool, params={"agency": True}, headers=_headers(admin))
    for_member = client.get(tool, params={"agency": True}, headers=_headers(member))
    plain = client.get(tool, headers=_headers(member))

    assert for_admin.status_code == 200, for_admin.text
    answer = for_admin.json()
    assert answer["data"]["agency_usage"]["cost_usd"] == 32.32
    assert [w["name"] for w in answer["data"]["agency_usage"]["workspaces"]] == [
        "Bright Dental",
        "Northfield Group",
    ]
    assert any("bill each client" in rule for rule in answer["rules"])
    assert for_member.status_code == 403
    assert "Only Admins" in for_member.json()["detail"]["error"]
    # A Member's assistant still reads its own workspace's usage.
    assert plain.status_code == 200
    assert plain.json()["data"]["agency_usage"] is None
