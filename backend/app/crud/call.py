import uuid
from datetime import UTC, datetime

from sqlalchemy import Table, func, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, select

from app.models.agent import Agent
from app.models.call import Call, CallPublic
from app.models.integration import Integration
from app.models.test_case import TestCase
from app.services.retell import RetellCall
from app.services.vapi import VapiCall

# SQLModel's declarative metaclass sets ``__table__`` at class creation, but
# pyright's stubs don't expose it on ``type[Call]``; bind it once with an
# explicit ``Table`` annotation so downstream usage typechecks cleanly.
_CALL_TABLE: Table = Call.__table__  # type: ignore[attr-defined]
_AGENT_TABLE: Table = Agent.__table__  # type: ignore[attr-defined]


def _retell_call_to_row(
    call: RetellCall, *, agent_id: uuid.UUID, integration_id: uuid.UUID
) -> dict:
    started_at = (
        datetime.fromtimestamp(call.start_timestamp / 1000, tz=UTC)
        if call.start_timestamp
        else datetime.now(UTC)
    )
    duration: int | None = None
    if call.start_timestamp and call.end_timestamp:
        duration = max(0, (call.end_timestamp - call.start_timestamp) // 1000)
    return {
        "agent_id": agent_id,
        "integration_id": integration_id,
        "retell_call_id": call.call_id,
        "retell_agent_id": call.agent_id or "",
        "started_at": started_at,
        "duration_seconds": duration,
        "status": call.call_status,
        "transcript": call.transcript_object,
        "raw": call.raw,
    }


def _vapi_call_to_row(
    call: VapiCall, *, agent_id: uuid.UUID, integration_id: uuid.UUID
) -> dict:
    started_at = call.started_at or call.created_at or datetime.now(UTC)
    duration: int | None = None
    if call.started_at and call.ended_at:
        duration = max(0, int((call.ended_at - call.started_at).total_seconds()))
    return {
        "agent_id": agent_id,
        "integration_id": integration_id,
        "retell_call_id": call.call_id,
        "retell_agent_id": call.assistant_id or "",
        "started_at": started_at,
        "duration_seconds": duration,
        "status": call.status,
        "transcript": call.transcript,
        "raw": call.raw,
    }


def upsert_calls_from_retell(
    *,
    session: Session,
    agent_id: uuid.UUID,
    integration_id: uuid.UUID,
    retell_calls: list[RetellCall],
) -> int:
    """Insert retell calls, skipping rows whose ``retell_call_id`` already exists.

    Returns the number of newly-inserted rows.
    """
    if not retell_calls:
        return 0

    rows = [
        _retell_call_to_row(c, agent_id=agent_id, integration_id=integration_id)
        for c in retell_calls
        if c.call_id
    ]
    if not rows:
        return 0

    stmt = (
        pg_insert(_CALL_TABLE)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["retell_call_id", "agent_id"])
        .returning(_CALL_TABLE.c.id)
    )
    result = session.execute(stmt)
    inserted = len(list(result))
    session.commit()
    return inserted


def upsert_calls_from_vapi(
    *,
    session: Session,
    agent_id: uuid.UUID,
    integration_id: uuid.UUID,
    vapi_calls: list[VapiCall],
) -> int:
    """Upsert Vapi calls, refreshing existing rows as calls evolve.

    Vapi calls can first arrive as in-progress and later transition to ended with
    transcript + duration populated. Use conflict-update semantics so refresh
    syncs can enrich existing rows instead of dropping updates as duplicates.
    """
    if not vapi_calls:
        return 0

    rows = [
        _vapi_call_to_row(c, agent_id=agent_id, integration_id=integration_id)
        for c in vapi_calls
        if c.call_id
    ]
    if not rows:
        return 0

    insert_stmt = pg_insert(_CALL_TABLE).values(rows)
    stmt = (
        insert_stmt
        .on_conflict_do_update(
            index_elements=["retell_call_id", "agent_id"],
            set_={
                "retell_agent_id": insert_stmt.excluded.retell_agent_id,
                "started_at": insert_stmt.excluded.started_at,
                "status": insert_stmt.excluded.status,
                "duration_seconds": func.coalesce(
                    insert_stmt.excluded.duration_seconds,
                    _CALL_TABLE.c.duration_seconds,
                ),
                "transcript": func.coalesce(
                    insert_stmt.excluded.transcript,
                    _CALL_TABLE.c.transcript,
                ),
                "raw": func.coalesce(
                    insert_stmt.excluded.raw,
                    _CALL_TABLE.c.raw,
                ),
                "integration_id": insert_stmt.excluded.integration_id,
            },
        )
        .returning(_CALL_TABLE.c.id)
    )
    result = session.execute(stmt)
    inserted = len(list(result))
    session.commit()
    return inserted


def get_latest_call_started_at(
    *,
    session: Session,
    agent_id: uuid.UUID,
    retell_agent_id: str | None = None,
) -> datetime | None:
    stmt = (
        select(func.max(Call.started_at))
        .where(Call.agent_id == agent_id)
        .where(Call.deleted_at.is_(None))  # type: ignore[union-attr]
    )
    if retell_agent_id is not None:
        stmt = stmt.where(Call.retell_agent_id == retell_agent_id)
    return session.exec(stmt).one_or_none()


def list_calls_for_agent(
    *,
    session: Session,
    agent_id: uuid.UUID,
    skip: int = 0,
    limit: int = 25,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[CallPublic], int]:
    base = (
        select(Call, Integration.provider)
        .outerjoin(Integration, Call.integration_id == Integration.id)
        .where(Call.agent_id == agent_id)
        .where(Call.deleted_at.is_(None))  # type: ignore[union-attr]
    )
    count_stmt = (
        select(func.count())
        .select_from(Call)
        .where(Call.agent_id == agent_id)
        .where(Call.deleted_at.is_(None))  # type: ignore[union-attr]
    )
    if date_from is not None:
        base = base.where(Call.started_at >= date_from)
        count_stmt = count_stmt.where(Call.started_at >= date_from)
    if date_to is not None:
        base = base.where(Call.started_at <= date_to)
        count_stmt = count_stmt.where(Call.started_at <= date_to)

    total = session.exec(count_stmt).one()
    rows = list(
        session.exec(
            base.order_by(col(Call.started_at).desc()).offset(skip).limit(limit)
        ).all()
    )
    if not rows:
        return [], total

    calls = [call for call, _ in rows]
    call_ids = [c.id for c in calls]
    provider_by_call_id = {call.id: provider for call, provider in rows}

    tc_counts = dict(
        session.exec(
            select(TestCase.source_call_id, func.count(TestCase.id))
            .where(col(TestCase.source_call_id).in_(call_ids))
            .group_by(TestCase.source_call_id)
        ).all()
    )

    items = [
        CallPublic(
            id=r.id,
            agent_id=r.agent_id,
            retell_call_id=r.retell_call_id,
            retell_agent_id=r.retell_agent_id,
            started_at=r.started_at,
            duration_seconds=r.duration_seconds,
            status=r.status,
            provider=provider_by_call_id.get(r.id),
            transcript=r.transcript,
            is_new=r.seen_at is None,
            test_case_count=int(tc_counts.get(r.id, 0)),
            created_at=r.created_at,
        )
        for r in calls
    ]
    return items, total


def mark_call_seen(*, session: Session, call_id: uuid.UUID) -> None:
    stmt = (
        update(_CALL_TABLE)
        .where(_CALL_TABLE.c.id == call_id)
        .where(_CALL_TABLE.c.seen_at.is_(None))
        .values(seen_at=datetime.now(UTC))
    )
    session.execute(stmt)
    session.commit()


def get_call(*, session: Session, call_id: uuid.UUID) -> Call | None:
    call = session.get(Call, call_id)
    if call is None or call.deleted_at is not None:
        return None
    return call


def count_calls_for_agent(*, session: Session, agent_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(Call)
        .where(Call.agent_id == agent_id)
        .where(Call.deleted_at.is_(None))  # type: ignore[union-attr]
    )
    return int(session.exec(stmt).one())


def soft_delete_calls_for_integration(
    *, session: Session, integration_id: uuid.UUID
) -> None:
    """Mark every call belonging to this integration as deleted and unlink the FK.

    The row stays so test cases that reference ``source_call_id`` keep their FK
    target. Reads in this module filter ``deleted_at IS NULL``.
    """
    stmt = (
        update(_CALL_TABLE)
        .where(_CALL_TABLE.c.integration_id == integration_id)
        .where(_CALL_TABLE.c.deleted_at.is_(None))
        .values(deleted_at=datetime.now(UTC), integration_id=None)
    )
    session.execute(stmt)


def touch_calls_last_synced_at(
    *, session: Session, agent_id: uuid.UUID, value: datetime | None = None
) -> None:
    """Stamp the agent's stale-while-revalidate marker.

    Pass ``value=None`` (the default) to use ``now()``; pass an explicit
    datetime to e.g. clear the stamp. Commits before returning so concurrent
    requests in other sessions see the updated timestamp.
    """
    stamp = value if value is not None else datetime.now(UTC)
    session.execute(
        update(_AGENT_TABLE)
        .where(_AGENT_TABLE.c.id == agent_id)
        .values(calls_last_synced_at=stamp)
    )
    session.commit()
