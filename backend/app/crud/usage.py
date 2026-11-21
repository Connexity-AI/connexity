"""Recording and reading usage records (`app/models/usage.py`)."""

import logging
import math
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import Date, cast, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, select

from app.models import Call, ModelAnswer, TestCaseResult, UsageRecord
from app.models.enums import TraceSource, TurnRole, UsageMeter

logger = logging.getLogger(__name__)

_TABLE = UsageRecord.__table__  # type: ignore[attr-defined]


def observed_minutes(call: Call) -> int:
    """A real call's length, each started minute counted whole (Dmytro, 2026-11-21).
    Nothing for a call without an end, a test call or a simulation."""
    if call.source is not TraceSource.PRODUCTION or call.ended_at is None:
        return 0
    seconds = (call.ended_at - call.started_at).total_seconds()
    return math.ceil(seconds / 60) if seconds > 0 else 0


def caller_messages(transcript: Sequence[dict[str, Any]] | None) -> int:
    """The messages the simulated caller sent, whatever became of the call."""
    return sum(1 for turn in transcript or [] if turn.get("role") == TurnRole.USER)


def _upsert(session: Session, values: dict[str, Any]) -> None:
    now = datetime.now(UTC)
    insert_stmt = pg_insert(_TABLE).values(
        id=uuid.uuid4(), created_at=now, updated_at=now, **values
    )
    kept = ("id", "created_at", "source_key", "company_id")
    session.execute(
        insert_stmt.on_conflict_do_update(
            constraint="uq_usage_record_source_key",
            set_={
                key: insert_stmt.excluded[key]
                for key in (*values, "updated_at")
                if key not in kept
            },
        )
    )


def record_call_usage(*, session: Session, call: Call) -> None:
    """Write, replace or remove the usage record of a real call. Commits.

    Called whenever the call is stored and whenever a model check on it is paid for,
    so a late end time or a late check never counts the call twice.
    """
    key = f"call:{call.id}"
    minutes = observed_minutes(call)
    if minutes == 0:
        session.execute(delete(UsageRecord).where(col(UsageRecord.source_key) == key))
        session.commit()
        return
    cost, tokens_in, tokens_out, model = session.exec(
        select(
            func.coalesce(func.sum(col(ModelAnswer.cost_usd)), 0.0),
            func.coalesce(func.sum(col(ModelAnswer.input_tokens)), 0),
            func.coalesce(func.sum(col(ModelAnswer.output_tokens)), 0),
            func.coalesce(func.max(col(ModelAnswer.model)), ""),
        ).where(ModelAnswer.call_id == call.id)
    ).one()
    _upsert(
        session,
        {
            "company_id": call.company_id,
            "agent_id": call.agent_id,
            "meter": UsageMeter.OBSERVED_MINUTES.value,
            "quantity": minutes,
            "occurred_at": call.started_at.replace(tzinfo=UTC),
            "source_key": key,
            "call_id": call.id,
            "own_cost_usd": float(cost),
            "model": model,
            "input_tokens": int(tokens_in),
            "output_tokens": int(tokens_out),
        },
    )
    session.commit()


def record_call_usage_safely(*, session: Session, call: Call) -> None:
    """`record_call_usage`, for where the call itself must be stored whatever happens
    to its usage record: a failure is logged and the next store writes the record."""
    try:
        record_call_usage(session=session, call=call)
    except Exception:
        session.rollback()
        logger.exception("Recording usage failed for call %s", call.id)


def record_simulated_usage(
    *,
    session: Session,
    result: TestCaseResult,
    agent_id: uuid.UUID,
    model: str,
    own_cost_usd: float,
    tokens: dict[str, int],
) -> None:
    """Write the usage record of a simulated call that has finished. Commits.

    ``tokens`` is the provider's usage summed over the simulated caller and the judge.
    """
    messages = caller_messages(result.transcript)
    if messages == 0:
        return
    _upsert(
        session,
        {
            "company_id": result.company_id,
            "agent_id": agent_id,
            "meter": UsageMeter.SIMULATED_CALLER_MESSAGES.value,
            "quantity": messages,
            "occurred_at": result.completed_at or datetime.now(UTC),
            "source_key": f"simulated:{result.id}",
            "test_case_result_id": result.id,
            "run_id": result.run_id,
            "own_cost_usd": own_cost_usd,
            "model": model,
            "input_tokens": tokens.get("prompt_tokens", 0),
            "output_tokens": tokens.get("completion_tokens", 0),
            "cache_read_tokens": tokens.get("cache_read_input_tokens", 0),
            "cache_write_tokens": tokens.get("cache_creation_input_tokens", 0),
        },
    )
    session.commit()


def _window(
    company_id: uuid.UUID,
    starts_at: datetime,
    ends_at: datetime,
    agent_id: uuid.UUID | None,
) -> list[Any]:
    window = [
        col(UsageRecord.company_id) == company_id,
        col(UsageRecord.occurred_at) >= starts_at,
        col(UsageRecord.occurred_at) < ends_at,
    ]
    if agent_id is not None:
        window.append(col(UsageRecord.agent_id) == agent_id)
    return window


def usage_by_agent(
    *,
    session: Session,
    company_id: uuid.UUID,
    starts_at: datetime,
    ends_at: datetime,
    agent_id: uuid.UUID | None = None,
) -> list[tuple[uuid.UUID, UsageMeter, int]]:
    rows = session.exec(
        select(
            UsageRecord.agent_id,
            UsageRecord.meter,
            func.sum(col(UsageRecord.quantity)),
        )
        .where(*_window(company_id, starts_at, ends_at, agent_id))
        .group_by(col(UsageRecord.agent_id), col(UsageRecord.meter))
    ).all()
    return [
        (agent, UsageMeter(meter), int(quantity)) for agent, meter, quantity in rows
    ]


def usage_by_run(
    *,
    session: Session,
    company_id: uuid.UUID,
    starts_at: datetime,
    ends_at: datetime,
    agent_id: uuid.UUID | None = None,
) -> list[tuple[uuid.UUID, uuid.UUID, int, int, datetime]]:
    """Per run with usage in the window: run, agent, simulated calls, caller messages
    and its first record's time; most messages first."""
    messages = func.sum(col(UsageRecord.quantity))
    first = func.min(col(UsageRecord.occurred_at))
    rows = session.exec(
        select(
            UsageRecord.run_id,
            UsageRecord.agent_id,
            func.count(),
            messages,
            first,
        )
        .where(
            *_window(company_id, starts_at, ends_at, agent_id),
            col(UsageRecord.meter) == UsageMeter.SIMULATED_CALLER_MESSAGES,
            col(UsageRecord.run_id).is_not(None),
        )
        .group_by(col(UsageRecord.run_id), col(UsageRecord.agent_id))
        .order_by(messages.desc(), first.desc())
    ).all()
    return [(run, agent, int(n), int(m), at) for run, agent, n, m, at in rows]


def observed_by_day(
    *,
    session: Session,
    company_id: uuid.UUID,
    starts_at: datetime,
    ends_at: datetime,
    agent_id: uuid.UUID | None = None,
    limit: int = 3,
) -> list[tuple[uuid.UUID, date, int]]:
    """An agent's observed minutes per UTC day, the biggest days first."""
    day = cast(func.timezone("UTC", col(UsageRecord.occurred_at)), Date)
    minutes = func.sum(col(UsageRecord.quantity))
    rows = session.exec(
        select(UsageRecord.agent_id, day, minutes)
        .where(
            *_window(company_id, starts_at, ends_at, agent_id),
            col(UsageRecord.meter) == UsageMeter.OBSERVED_MINUTES,
        )
        .group_by(col(UsageRecord.agent_id), day)
        .order_by(minutes.desc(), day.desc())
        .limit(limit)
    ).all()
    return [(agent, on, int(m)) for agent, on, m in rows]
