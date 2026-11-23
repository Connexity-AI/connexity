"""What Anthropic billed for a day, stored beside what Connexity recorded (plan
`plans/2026-11-23-anthropic-cost-comparison.md`). Every report answer is invented."""

import time
import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from typing import Any

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.core.config import settings
from app.models import UsageRecord
from app.models.enums import UsageMeter
from app.models.provider_cost import ProviderCostDay
from app.services import provider_cost
from app.services.provider_cost import (
    COST_REPORT,
    USAGE_REPORT,
    read_provider_costs,
)
from app.tests.api.routes.test_call_pull import (  # noqa: F401
    PULL,
    _isolated,
    _scheduler,
    _token,
)
from app.tests.api.routes.test_mcp_issues import _agent, _person

# Far from today, so no other test's usage lands in these days.
NOW = datetime(2020, 3, 10, 9, tzinfo=UTC)
HAIKU = "claude-haiku-5-5"
FIRST, LAST = datetime(2020, 3, 1, tzinfo=UTC), datetime(2020, 3, 20, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _clean(db: Session, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(settings, "ANTHROPIC_ADMIN_KEY", "invented-admin-key")
    monkeypatch.setattr(provider_cost, "_next_read", None)

    def wipe() -> None:
        db.exec(delete(ProviderCostDay))  # type: ignore[call-overload]
        db.exec(  # type: ignore[call-overload]
            delete(UsageRecord).where(
                col(UsageRecord.occurred_at) >= FIRST,
                col(UsageRecord.occurred_at) < LAST,
            )
        )
        db.commit()

    wipe()
    yield
    wipe()


def _bucket(day: str, *results: dict[str, Any]) -> dict[str, Any]:
    return {"starting_at": f"{day}T00:00:00Z", "results": list(results)}


def _reports(
    costs: list[dict[str, Any]], used: list[dict[str, Any]]
) -> tuple[respx.Route, respx.Route]:
    return (
        respx.get(COST_REPORT).respond(json={"data": costs, "has_more": False}),
        respx.get(USAGE_REPORT).respond(json={"data": used, "has_more": False}),
    )


def _record(
    db: Session, at: datetime, *, usd: float, tokens: tuple[int, int], model: str
) -> None:
    user = _person(db)
    agent = _agent(db, user, "Front desk")
    db.add(
        UsageRecord(
            company_id=agent.company_id,
            agent_id=agent.id,
            meter=UsageMeter.SIMULATED_CALLER_MESSAGES,
            quantity=1,
            occurred_at=at,
            source_key=f"simulated:{uuid.uuid4()}",
            own_cost_usd=usd,
            model=model,
            input_tokens=tokens[0],
            output_tokens=tokens[1],
        )
    )
    db.commit()


def _days(db: Session) -> dict[tuple[date, str], ProviderCostDay]:
    db.expire_all()
    return {(row.day, row.model): row for row in db.exec(select(ProviderCostDay)).all()}


@respx.mock
async def test_a_day_holds_what_was_billed_beside_what_was_recorded(
    db: Session,
) -> None:
    # Two workspaces recorded on the 9th; a call on another provider's model and one
    # just after midnight UTC belong elsewhere.
    _record(
        db,
        datetime(2020, 3, 9, 10, tzinfo=UTC),
        usd=0.03,
        tokens=(300_000, 9_000),
        model=HAIKU,
    )
    _record(
        db,
        datetime(2020, 3, 9, 23, 59, tzinfo=UTC),
        usd=0.01,
        tokens=(100_000, 1_000),
        model=HAIKU,
    )
    _record(
        db,
        datetime(2020, 3, 9, 12, tzinfo=UTC),
        usd=0.5,
        tokens=(9, 9),
        model="jev-1.14.0",
    )
    _record(
        db,
        datetime(2020, 3, 10, 0, 1, tzinfo=UTC),
        usd=0.002,
        tokens=(20_000, 0),
        model=HAIKU,
    )
    cost, used = _reports(
        [
            _bucket(
                "2020-03-09",
                # Cents, one line per kind of token.
                {
                    "amount": "4.0",
                    "model": HAIKU,
                    "token_type": "uncached_input_tokens",
                },
                {"amount": "0.5", "model": HAIKU, "token_type": "output_tokens"},
            ),
            _bucket("2020-03-10"),
        ],
        [
            _bucket(
                "2020-03-09",
                {
                    "model": HAIKU,
                    "uncached_input_tokens": 400_000,
                    "output_tokens": 10_000,
                    "cache_read_input_tokens": 7,
                    "cache_creation": {
                        "ephemeral_1h_input_tokens": 2,
                        "ephemeral_5m_input_tokens": 3,
                    },
                },
            )
        ],
    )

    assert await read_provider_costs(session=db, now=NOW) == 2

    # The days not final yet are asked for: three back, up to the end of today.
    for route in (cost, used):
        sent = route.calls.last.request
        assert sent.headers["x-api-key"] == "invented-admin-key"
        assert sent.url.params["starting_at"] == "2020-03-07T00:00:00Z"
        assert sent.url.params["ending_at"] == "2020-03-11T00:00:00Z"
    days = _days(db)
    assert set(days) == {(date(2020, 3, 9), HAIKU), (date(2020, 3, 10), HAIKU)}
    ninth = days[(date(2020, 3, 9), HAIKU)]
    assert ninth.provider == "anthropic"
    assert (ninth.billed_usd, ninth.recorded_usd) == (0.045, 0.04)
    assert (ninth.billed_input_tokens, ninth.recorded_input_tokens) == (
        400_000,
        400_000,
    )
    assert (ninth.billed_output_tokens, ninth.recorded_output_tokens) == (
        10_000,
        10_000,
    )
    assert (ninth.billed_cache_read_tokens, ninth.billed_cache_write_tokens) == (7, 5)
    # Recorded and not billed yet: the report runs behind.
    tenth = days[(date(2020, 3, 10), HAIKU)]
    assert (tenth.billed_usd, tenth.recorded_usd) == (0.0, 0.002)


@respx.mock
async def test_a_day_is_read_again_and_replaced_not_doubled(db: Session) -> None:
    _reports([_bucket("2020-03-09", {"amount": "1.0", "model": HAIKU})], [])
    assert await read_provider_costs(session=db, now=NOW) == 1
    # Not due again for hours.
    assert await read_provider_costs(session=db, now=NOW) is None

    # The report caught up; a cost no model is named for gets its own row.
    _reports(
        [
            _bucket(
                "2020-03-09",
                {"amount": "2.5", "model": HAIKU},
                {"amount": "10", "model": None},
            )
        ],
        [],
    )
    assert await read_provider_costs(session=db, now=NOW, force=True) == 2
    days = _days(db)
    assert days[(date(2020, 3, 9), HAIKU)].billed_usd == 0.025
    assert days[(date(2020, 3, 9), "")].billed_usd == 0.1


@respx.mock
async def test_the_report_is_read_page_by_page(db: Session) -> None:
    def cost(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("page") == "p2":
            page = {"data": [_bucket("2020-03-09", {"amount": "3", "model": HAIKU})]}
        else:
            page = {
                "data": [_bucket("2020-03-08", {"amount": "1", "model": HAIKU})],
                "has_more": True,
                "next_page": "p2",
            }
        return httpx.Response(200, json=page)

    respx.get(COST_REPORT).mock(side_effect=cost)
    respx.get(USAGE_REPORT).respond(json={"data": []})

    assert await read_provider_costs(session=db, now=NOW) == 2
    assert {k[0].day: v.billed_usd for k, v in _days(db).items()} == {8: 0.01, 9: 0.03}


async def test_without_an_admin_key_nothing_is_read(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ANTHROPIC_ADMIN_KEY", None)
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(COST_REPORT)
        assert await read_provider_costs(session=db, now=NOW) is None
    assert not route.called and _days(db) == {}


@pytest.mark.parametrize(
    "answer",
    [
        httpx.ConnectTimeout("timed out"),
        httpx.Response(401, json={"error": {"message": "not an admin key"}}),
        httpx.Response(200, content=b""),
        httpx.Response(200, json={"data": [{"results": "not a list"}]}),
        httpx.Response(200, json={"data": [_bucket("2020-03-09", {"model": HAIKU})]}),
    ],
    ids=["timeout", "refused", "empty", "malformed", "no-amount"],
)
@respx.mock
async def test_a_failed_read_leaves_the_table_as_it_was(
    db: Session, answer: httpx.Response | Exception
) -> None:
    _reports([_bucket("2020-03-09", {"amount": "1.0", "model": HAIKU})], [])
    assert await read_provider_costs(session=db, now=NOW) == 1

    if isinstance(answer, Exception):
        respx.get(COST_REPORT).mock(side_effect=answer)
    else:
        respx.get(COST_REPORT).mock(return_value=answer)
    assert await read_provider_costs(session=db, now=NOW, force=True) is None
    assert _days(db)[(date(2020, 3, 9), HAIKU)].billed_usd == 0.01
    # It is tried again minutes later, not hours.
    assert provider_cost._next_read is not None
    assert provider_cost._next_read - time.monotonic() <= provider_cost.RETRY_EVERY


@pytest.mark.usefixtures("_scheduler")
@respx.mock
def test_the_scheduled_call_pull_reads_it(client: TestClient, db: Session) -> None:
    today = datetime.now(UTC).date().isoformat()
    cost, _ = _reports(
        [_bucket(today, {"amount": "7", "model": "claude-invented"})], []
    )
    headers = {"Authorization": f"Bearer {_token()}"}

    assert client.post(PULL, headers=headers).status_code == 200
    assert _days(db)[(date.fromisoformat(today), "claude-invented")].billed_usd == 0.07
    # The next minute's pull does not ask again.
    assert client.post(PULL, headers=headers).status_code == 200
    assert cost.call_count == 1
