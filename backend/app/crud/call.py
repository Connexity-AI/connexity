import uuid
from datetime import UTC, datetime

from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, select

from app.models.call import Call, CallPublic
from app.models.test_case import TestCase
from app.services.retell import RetellCall


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
        pg_insert(Call.__table__)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["retell_call_id"])
        .returning(Call.__table__.c.id)
    )
    result = session.execute(stmt)
    inserted = len(list(result))
    session.commit()
    return inserted


def get_latest_call_started_at(
    *, session: Session, agent_id: uuid.UUID
) -> datetime | None:
    stmt = select(func.max(Call.started_at)).where(Call.agent_id == agent_id)
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
    base = select(Call).where(Call.agent_id == agent_id)
    count_stmt = select(func.count()).select_from(Call).where(Call.agent_id == agent_id)
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

    call_ids = [r.id for r in rows]

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
            transcript=r.transcript,
            is_new=r.seen_at is None,
            test_case_count=int(tc_counts.get(r.id, 0)),
            created_at=r.created_at,
        )
        for r in rows
    ]
    return items, total


def mark_call_seen(*, session: Session, call_id: uuid.UUID) -> None:
    stmt = (
        update(Call.__table__)
        .where(Call.__table__.c.id == call_id)
        .where(Call.__table__.c.seen_at.is_(None))
        .values(seen_at=datetime.now(UTC))
    )
    session.execute(stmt)
    session.commit()


def get_call(*, session: Session, call_id: uuid.UUID) -> Call | None:
    return session.get(Call, call_id)


def count_calls_for_agent(*, session: Session, agent_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(Call).where(Call.agent_id == agent_id)
    return int(session.exec(stmt).one())
