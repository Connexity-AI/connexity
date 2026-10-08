import uuid
from datetime import UTC, datetime

from sqlalchemy import Table, func, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, select

from app.models.agent import Agent
from app.models.call import Call, CallPublic
from app.models.enums import CallLabel
from app.models.test_case import TestCase
from app.services.elevenlabs import (
    ElevenLabsConversationDetails,
    ElevenLabsConversationSummary,
)
from app.services.vapi import VapiCall

# SQLModel's declarative metaclass sets ``__table__`` at class creation, but
# pyright's stubs don't expose it on ``type[Call]``; bind it once with an
# explicit ``Table`` annotation so downstream usage typechecks cleanly.
_CALL_TABLE: Table = Call.__table__  # type: ignore[attr-defined]
_AGENT_TABLE: Table = Agent.__table__  # type: ignore[attr-defined]


def _vapi_call_to_row(
    call: VapiCall,
    *,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    integration_id: uuid.UUID,
) -> dict:
    started_at = call.started_at or call.created_at or datetime.now(UTC)
    return {
        "agent_id": agent_id,
        "company_id": company_id,
        "integration_id": integration_id,
        "provider": "vapi",
        "external_id": call.call_id,
        "provider_agent_id": call.assistant_id or "",
        "started_at": started_at,
        "raw": call.raw,
    }


def _elevenlabs_summary_to_row(
    call: ElevenLabsConversationSummary,
    *,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    integration_id: uuid.UUID,
) -> dict:
    started_at = datetime.fromtimestamp(call.start_time_unix_secs, tz=UTC)
    return {
        "agent_id": agent_id,
        "company_id": company_id,
        "integration_id": integration_id,
        "provider": "elevenlabs",
        "external_id": call.conversation_id,
        "provider_agent_id": call.agent_id,
        "started_at": started_at,
        "raw": call.raw,
    }


def _elevenlabs_details_to_row(
    call: ElevenLabsConversationDetails,
    *,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    integration_id: uuid.UUID,
) -> dict:
    started_at = datetime.fromtimestamp(call.start_time_unix_secs, tz=UTC)
    return {
        "agent_id": agent_id,
        "company_id": company_id,
        "integration_id": integration_id,
        "provider": "elevenlabs",
        "external_id": call.conversation_id,
        "provider_agent_id": call.agent_id or "",
        "started_at": started_at,
        "raw": call.raw,
    }


def upsert_calls_from_vapi(
    *,
    session: Session,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    integration_id: uuid.UUID,
    vapi_calls: list[VapiCall],
) -> int:
    """Upsert Vapi calls, refreshing existing rows as calls evolve.

    Vapi calls can first arrive as in-progress and later transition to ended. Use
    conflict-update semantics so a refresh replaces the stored payload instead of
    dropping the update as a duplicate.
    """
    if not vapi_calls:
        return 0

    rows = [
        _vapi_call_to_row(
            c,
            agent_id=agent_id,
            company_id=company_id,
            integration_id=integration_id,
        )
        for c in vapi_calls
        if c.call_id
    ]
    if not rows:
        return 0

    insert_stmt = pg_insert(_CALL_TABLE).values(rows)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["external_id", "agent_id"],
        set_={
            "provider_agent_id": insert_stmt.excluded.provider_agent_id,
            "started_at": insert_stmt.excluded.started_at,
            "raw": func.coalesce(
                insert_stmt.excluded.raw,
                _CALL_TABLE.c.raw,
            ),
            "integration_id": insert_stmt.excluded.integration_id,
        },
    ).returning(_CALL_TABLE.c.id)
    result = session.execute(stmt)
    inserted = len(list(result))
    session.commit()
    return inserted


def upsert_calls_from_elevenlabs(
    *,
    session: Session,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    integration_id: uuid.UUID,
    conversations: list[ElevenLabsConversationDetails | ElevenLabsConversationSummary],
) -> int:
    if not conversations:
        return 0

    rows: list[dict] = []
    for c in conversations:
        if isinstance(c, ElevenLabsConversationDetails):
            rows.append(
                _elevenlabs_details_to_row(
                    c,
                    agent_id=agent_id,
                    company_id=company_id,
                    integration_id=integration_id,
                )
            )
        else:
            rows.append(
                _elevenlabs_summary_to_row(
                    c,
                    agent_id=agent_id,
                    company_id=company_id,
                    integration_id=integration_id,
                )
            )
    rows = [r for r in rows if r.get("external_id")]
    if not rows:
        return 0

    insert_stmt = pg_insert(_CALL_TABLE).values(rows)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["external_id", "agent_id"],
        set_={
            "provider_agent_id": insert_stmt.excluded.provider_agent_id,
            "started_at": insert_stmt.excluded.started_at,
            "raw": func.coalesce(
                insert_stmt.excluded.raw,
                _CALL_TABLE.c.raw,
            ),
            "integration_id": insert_stmt.excluded.integration_id,
        },
    ).returning(_CALL_TABLE.c.id)
    result = session.execute(stmt)
    inserted = len(list(result))
    session.commit()
    return inserted


def get_latest_call_started_at(
    *,
    session: Session,
    agent_id: uuid.UUID,
    provider_agent_id: str | None = None,
) -> datetime | None:
    stmt = (
        select(func.max(Call.started_at))
        .where(Call.agent_id == agent_id)
        .where(Call.deleted_at.is_(None))  # type: ignore[union-attr]
    )
    if provider_agent_id is not None:
        stmt = stmt.where(Call.provider_agent_id == provider_agent_id)
    return session.exec(stmt).one_or_none()


def call_to_public(call: Call, *, test_case_count: int) -> CallPublic:
    duration: int | None = None
    if call.ended_at is not None:
        duration = max(0, int((call.ended_at - call.started_at).total_seconds()))
    return CallPublic(
        id=call.id,
        agent_id=call.agent_id,
        provider=call.provider,
        external_id=call.external_id,
        provider_agent_id=call.provider_agent_id,
        source=call.source,
        started_at=call.started_at,
        ended_at=call.ended_at,
        duration_seconds=duration,
        end_reason=call.end_reason,
        end_reason_detail=call.end_reason_detail,
        has_trace=call.schema_version is not None,
        is_new=call.seen_at is None,
        test_case_count=test_case_count,
        label=call.label,
        created_at=call.created_at,
    )


def count_test_cases_for_call(*, session: Session, call_id: uuid.UUID) -> int:
    return int(
        session.exec(
            select(func.count(TestCase.id)).where(TestCase.source_call_id == call_id)
        ).one()
    )


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
        select(Call).where(Call.agent_id == agent_id).where(Call.deleted_at.is_(None))  # type: ignore[union-attr]
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
    calls = list(
        session.exec(
            base.order_by(col(Call.started_at).desc()).offset(skip).limit(limit)
        ).all()
    )
    if not calls:
        return [], total

    call_ids = [c.id for c in calls]

    tc_counts = dict(
        session.exec(
            select(TestCase.source_call_id, func.count(TestCase.id))
            .where(col(TestCase.source_call_id).in_(call_ids))
            .group_by(TestCase.source_call_id)
        ).all()
    )

    items = [
        call_to_public(call, test_case_count=int(tc_counts.get(call.id, 0)))
        for call in calls
    ]
    return items, total


def set_call_label(
    *, session: Session, call_id: uuid.UUID, label: CallLabel | None
) -> Call | None:
    call = session.get(Call, call_id)
    if call is None:
        return None
    call.label = label
    session.add(call)
    session.commit()
    session.refresh(call)
    return call


def mark_call_seen(*, session: Session, call_id: uuid.UUID) -> None:
    stmt = (
        update(_CALL_TABLE)
        .where(_CALL_TABLE.c.id == call_id)
        .where(_CALL_TABLE.c.seen_at.is_(None))
        .values(seen_at=datetime.now(UTC))
    )
    session.execute(stmt)
    session.commit()


def get_call(
    *, session: Session, call_id: uuid.UUID, company_id: uuid.UUID | None = None
) -> Call | None:
    call = session.get(Call, call_id)
    if call is None or call.deleted_at is not None:
        return None
    if company_id is not None and call.company_id != company_id:
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
