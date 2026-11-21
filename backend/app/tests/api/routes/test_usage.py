"""Usage per workspace through MCP: observed minutes from real calls, simulated caller
messages from test runs, both at list price, on invented agents and calls with Retell
and the model mocked (plan `plans/2026-11-21-usage-per-workspace.md`)."""

import importlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import respx
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, col, delete, select

from app import crud
from app.crud.usage import caller_messages, record_simulated_usage
from app.models import Agent, UsageRecord, User
from app.models.call import Call
from app.models.enums import ModelAnswerStatus, TraceSource, UsageMeter
from app.models.test_case_result import TestCaseResult
from app.services.mappings.retell import retell_call_to_trace
from app.services.usage import window
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    _headers,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_scenarios import (
    API,
    PRICE,
    _person,
    _price,
    _ready,
    _scenarios,
    _set,
)
from app.tests.api.routes.test_test_runs import (
    PLAYGROUND,
    _agent_turn,
    _execute,
    _runs,
    _start,
    _verdict,
    caller,  # noqa: F401
)
from app.tests.utils.retell_payloads import retell_call


def _usage(client: TestClient, user: User, **params: Any) -> Any:
    return client.get(
        f"{API}/mcp/workspaces/{user.company_id}/usage",
        headers=_headers(user),
        params=params,
    )


def _real_call(
    db: Session,
    agent: Agent,
    *,
    seconds: int,
    call_id: str | None = None,
    source: TraceSource = TraceSource.PRODUCTION,
    started: datetime | None = None,
) -> Call:
    started = started or datetime.now(UTC) - timedelta(hours=1)
    payload = retell_call(
        call_id or f"call_{uuid.uuid4().hex[:10]}",
        start_ms=int(started.timestamp() * 1000),
        duration_ms=seconds * 1000,
    )
    trace = retell_call_to_trace(payload).model_copy(update={"source": source})
    return crud.store_trace(
        session=db,
        trace=trace,
        agent_id=agent.id,
        company_id=agent.company_id,
        raw=payload,
    ).call


def _clear(db: Session, agent: Agent) -> None:
    """Forget what the setup's own invented calls were counted as."""
    db.exec(delete(UsageRecord).where(col(UsageRecord.company_id) == agent.company_id))  # type: ignore[call-overload]
    db.commit()


def _line(data: dict[str, Any], meter: str) -> dict[str, Any]:
    return next(line for line in data["lines"] if line["meter"] == meter)


def test_a_real_call_counts_each_started_minute_once(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db, client)
    _clear(db, agent)

    call = _real_call(db, agent, seconds=95, call_id="call_usage_95")
    # Read again, as the pull does: the record is replaced, not added.
    _real_call(db, agent, seconds=95, call_id="call_usage_95")

    r = _usage(client, user)
    assert r.status_code == 200, r.text
    body = r.json()
    data = body["data"]
    assert _line(data, "observed_minutes") == {
        "meter": "observed_minutes",
        "unit": "minute of a real call, each started minute whole",
        "quantity": 2,
        "unit_price_usd": 0.03,
        "cost_usd": 0.06,
    }
    assert data["cost_usd"] == 0.06
    assert [(a["agent_id"], a["cost_usd"]) for a in data["agents"]] == [
        (str(agent.id), 0.06)
    ]
    assert data["movers"][0]["kind"] == "calls"
    assert "2 observed minutes, $0.06" in data["movers"][0]["line"]
    assert body["guide"] == "connexity://guides/usage"
    assert any("list price" in rule for rule in body["rules"])
    assert [m.strip() for m in data["period"].split()] == ["month"]

    # One agent only, and the same over the last 7 days.
    for params in ({"agent_id": str(agent.id)}, {"period": "7d"}):
        assert _usage(client, user, **params).json()["data"]["cost_usd"] == 0.06

    # What a model check on the call cost Connexity lands on its record, and in no
    # answer.
    crud.save_model_answer(
        session=db,
        call=call,
        check_type="invented_check",
        check_version=1,
        status=ModelAnswerStatus.OK,
        model="invented-model",
        input_tokens=1200,
        output_tokens=80,
        requests=1,
        cost_usd=0.004,
    )
    record = db.exec(select(UsageRecord).where(UsageRecord.call_id == call.id)).one()
    db.refresh(record)
    assert (record.quantity, record.own_cost_usd, record.input_tokens) == (
        2,
        0.004,
        1200,
    )
    answer = _usage(client, user).text
    assert "own_cost" not in answer
    assert "0.004" not in answer


def test_test_calls_and_calls_without_an_end_count_nothing(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db, client)
    _clear(db, agent)

    _real_call(db, agent, seconds=200, source=TraceSource.TEST_CALL)
    _real_call(db, agent, seconds=200, source=TraceSource.SIMULATION)
    _real_call(db, agent, seconds=0)

    data = _usage(client, user).json()
    assert data["data"]["cost_usd"] == 0
    assert _line(data["data"], "observed_minutes")["quantity"] == 0
    assert data["data"]["movers"] == []
    assert "Nothing was counted" in data["next_steps"][0]


def test_a_run_counts_its_caller_messages_on_the_run_and_the_agent(
    client: TestClient,
    db: Session,
    caller: AsyncMock,  # noqa: F811
) -> None:
    user, agent, keys = _ready(db, client)
    _clear(db, agent)
    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]
    _set(client, user, agent, "smoke", [scenario["id"]])

    def run() -> dict[str, Any]:
        started = _start(client, user, agent, set="smoke", repeats=2).json()
        judge = AsyncMock(return_value=_verdict(keys[PRICE], "passed"))
        with respx.mock() as retell:
            retell.post(url__startswith=PLAYGROUND).mock(side_effect=_agent_turn)
            with patch("app.services.rule_judge.call_llm", new=judge):
                _execute(started["data"]["run_id"])
        return started

    first = run()
    assert first["data"]["price_per_caller_message_usd"] == 0.02
    assert first["data"]["last_run"] is None
    run_id = first["data"]["run_id"]

    calls = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).all()
    messages = sum(caller_messages(c.transcript) for c in calls)
    assert messages == 2
    cost = round(messages * 0.02, 2)

    detail = _runs(client, user, agent, run_id=run_id).json()["data"]["run"]
    assert (detail["caller_messages"], detail["cost_usd"]) == (messages, cost)
    assert [(c["caller_messages"], c["cost_usd"]) for c in detail["calls"]] == [
        (1, 0.02),
        (1, 0.02),
    ]
    listed = _runs(client, user, agent).json()["data"]["runs"][0]
    assert (listed["caller_messages"], listed["cost_usd"]) == (messages, cost)

    data = _usage(client, user).json()["data"]
    assert _line(data, "simulated_caller_messages")["quantity"] == messages
    assert data["cost_usd"] == cost
    assert data["runs"] == [
        {
            "run_id": run_id,
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "set_name": "smoke",
            "started_at": data["runs"][0]["started_at"],
            "simulated_calls": 2,
            "caller_messages": messages,
            "cost_usd": cost,
        }
    ]
    assert data["movers"][0]["run_id"] == run_id
    assert f"{messages} caller messages, ${cost:.2f}" in data["movers"][0]["line"]

    # Connexity's own cost: the caller's and the judge's model calls, with their
    # tokens, in the table and in no answer.
    records = db.exec(
        select(UsageRecord).where(UsageRecord.run_id == uuid.UUID(run_id))
    ).all()
    assert len(records) == 2
    assert all(r.own_cost_usd == 0.002 for r in records)
    assert all(r.meter is UsageMeter.SIMULATED_CALLER_MESSAGES for r in records)
    for answer in (
        _usage(client, user).text,
        _runs(client, user, agent, run_id=run_id).text,
    ):
        assert "own_cost" not in answer
        assert "0.002" not in answer

    # The next run of the same set says what this one came to.
    second = run()
    assert second["data"]["last_run"] == {
        "run_id": run_id,
        "caller_messages": messages,
        "cost_usd": cost,
    }
    assert any(f"${cost:.2f}" in step for step in second["next_steps"])

    # Runs are paged.
    page = _usage(client, user, limit=1).json()
    assert len(page["data"]["runs"]) == 1
    assert page["next_cursor"]
    rest = _usage(client, user, limit=1, cursor=page["next_cursor"]).json()
    assert len(rest["data"]["runs"]) == 1
    assert rest["next_cursor"] is None
    assert rest["data"]["runs"][0]["run_id"] != page["data"]["runs"][0]["run_id"]

    # Another workspace sees none of it.
    other = _person(db)
    theirs = _usage(client, other).json()["data"]
    assert theirs["cost_usd"] == 0
    assert theirs["runs"] == []
    r = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/usage", headers=_headers(other)
    )
    assert r.status_code == 404, r.text
    r = _usage(client, other, agent_id=str(agent.id))
    assert r.status_code == 404, r.text


def test_a_simulated_call_that_stopped_with_an_error_counts_what_was_sent(
    client: TestClient,
    db: Session,
    caller: AsyncMock,  # noqa: F811
) -> None:
    user, agent, keys = _ready(db, client)
    _clear(db, agent)
    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]
    _set(client, user, agent, "smoke", [scenario["id"]])
    run_id = _start(client, user, agent, set="smoke").json()["data"]["run_id"]
    row = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).first()
    assert row is not None
    said = [
        {"index": i, "role": role, "content": content}
        for i, (role, content) in enumerate(
            [
                ("assistant", "Hello."),
                ("user", "One."),
                ("assistant", "Yes?"),
                ("user", "Two."),
                ("assistant", "Go on."),
                ("user", "Three."),
                ("assistant", "[platform: the platform stopped answering]"),
            ]
        )
    ]
    row.transcript = said
    row.error_message = "The conversation stopped: the platform stopped answering"
    row.completed_at = datetime.now(UTC)
    db.add(row)
    db.flush()
    for _ in range(2):  # stored twice: counted once
        record_simulated_usage(
            session=db,
            result=row,
            agent_id=agent.id,
            model="invented-model",
            own_cost_usd=0.001,
            tokens={"prompt_tokens": 900, "completion_tokens": 40},
        )
    db.commit()

    data = _usage(client, user).json()["data"]
    assert _line(data, "simulated_caller_messages")["quantity"] == 3
    assert data["cost_usd"] == 0.06


def test_the_period_is_a_calendar_month_or_days(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db, client)
    _clear(db, agent)
    _real_call(db, agent, seconds=61, started=datetime(2026, 3, 31, 23, 50, tzinfo=UTC))
    _real_call(db, agent, seconds=10, started=datetime(2026, 4, 1, 0, 5, tzinfo=UTC))

    now = datetime(2026, 12, 15, 10, tzinfo=UTC)
    assert window("month", None, now) == (
        datetime(2026, 12, 1, tzinfo=UTC),
        datetime(2027, 1, 1, tzinfo=UTC),
    )
    assert window("month", "2026-02", now) == (
        datetime(2026, 2, 1, tzinfo=UTC),
        datetime(2026, 3, 1, tzinfo=UTC),
    )
    assert window("7d", None, now)[0] == datetime(2026, 12, 8, 10, tzinfo=UTC)

    # A call belongs to the month it started in.
    march = _usage(client, user, month="2026-03").json()["data"]
    assert (march["cost_usd"], march["starts_at"]) == (0.06, "2026-03-01T00:00:00Z")
    assert "31 Mar" in march["movers"][0]["line"]
    assert _usage(client, user, month="2026-04").json()["data"]["cost_usd"] == 0.03
    assert _usage(client, user, month="2020-01").json()["data"]["cost_usd"] == 0
    assert _usage(client, user).json()["data"]["cost_usd"] == 0
    r = _usage(client, user, month="last")
    assert r.status_code == 422, r.text
    assert "YYYY-MM" in r.json()["detail"]["error"]
    assert _usage(client, user, period="year").status_code == 422


def test_the_migration_fills_in_what_recording_would_have_written(
    client: TestClient,
    db: Session,
    caller: AsyncMock,  # noqa: F811
) -> None:
    user, agent, keys = _ready(db, client)
    _real_call(db, agent, seconds=95)
    _real_call(db, agent, seconds=600, source=TraceSource.TEST_CALL)
    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]
    _set(client, user, agent, "smoke", [scenario["id"]])
    run_id = _start(client, user, agent, set="smoke", repeats=2).json()["data"][
        "run_id"
    ]
    judge = AsyncMock(return_value=_verdict(keys[PRICE], "passed"))
    with respx.mock() as retell:
        retell.post(url__startswith=PLAYGROUND).mock(side_effect=_agent_turn)
        with patch("app.services.rule_judge.call_llm", new=judge):
            _execute(run_id)

    def records() -> list[tuple[Any, ...]]:
        db.expire_all()
        return sorted(
            (r.source_key, r.meter, r.quantity, r.agent_id, r.run_id, r.own_cost_usd)
            for r in db.exec(
                select(UsageRecord).where(UsageRecord.company_id == agent.company_id)
            ).all()
        )

    recorded = records()
    assert len(recorded) >= 3

    _clear(db, agent)
    migration = importlib.import_module("app.alembic.versions.0044_usage_record")
    db.execute(text(migration.BACKFILL_CALLS))
    db.execute(text(migration.BACKFILL_SIMULATED))
    db.commit()

    assert records() == recorded


def test_a_call_that_broke_after_the_conversation_still_counts_it(
    client: TestClient,
    db: Session,
    caller: AsyncMock,  # noqa: F811
) -> None:
    user, agent, keys = _ready(db, client)
    _clear(db, agent)
    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]
    _set(client, user, agent, "smoke", [scenario["id"]])
    run_id = _start(client, user, agent, set="smoke", repeats=1).json()["data"][
        "run_id"
    ]
    judge = AsyncMock(return_value=_verdict(keys[PRICE], "passed"))
    with respx.mock() as retell:
        retell.post(url__startswith=PLAYGROUND).mock(side_effect=_agent_turn)
        with (
            patch("app.services.rule_judge.call_llm", new=judge),
            patch(
                "app.services.test_run.check_simulated",
                side_effect=RuntimeError("invented failure"),
            ),
        ):
            _execute(run_id)

    row = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).one()
    assert row.error_message == "invented failure"
    assert caller_messages(row.transcript) == 1
    record = db.exec(
        select(UsageRecord).where(UsageRecord.test_case_result_id == row.id)
    ).one()
    # The caller's model call and the judge's were both paid for.
    assert (record.quantity, record.own_cost_usd) == (1, 0.002)


def test_a_failed_usage_record_never_stops_a_call_being_stored(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db, client)
    _clear(db, agent)

    with patch("app.crud.usage._upsert", side_effect=RuntimeError("invented")):
        call = _real_call(db, agent, seconds=95, call_id="call_usage_guarded")
    assert call.id is not None
    assert _usage(client, user).json()["data"]["cost_usd"] == 0

    # The next store writes it.
    _real_call(db, agent, seconds=95, call_id="call_usage_guarded")
    assert _usage(client, user).json()["data"]["cost_usd"] == 0.06
