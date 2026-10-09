"""Store a call trace as rows and assemble it back.

Each part of a trace is stored once: call-level fields on the call row, one row per
event, one row per component. There is no stored trace document.
"""

import uuid
from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, delete, select

from app.models.call import Call, CallComponent, CallEvent
from app.models.component_version import STATE_KINDS
from app.models.enums import CallEventType
from app.models.trace import (
    MarkerEvent,
    ToolCallEvent,
    Trace,
    TraceComponent,
    TraceEvent,
    TraceParties,
    UtteranceEvent,
)
from app.services.fingerprint import combined_fingerprint

_CALL_TABLE: Table = Call.__table__  # type: ignore[attr-defined]


def _to_naive_utc(value: datetime) -> datetime:
    # Call timestamps are stored naive, in UTC, like the rest of the call table.
    return value.astimezone(UTC).replace(tzinfo=None)


def _to_aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC)


def _event_row(
    event: TraceEvent, *, seq: int, call_id: uuid.UUID, company_id: uuid.UUID
) -> CallEvent:
    row = CallEvent(
        company_id=company_id,
        call_id=call_id,
        seq=seq,
        key=event.id,
        type=event.type,
        start_ms=event.start_ms,
        span_id=event.span_id,
    )
    if isinstance(event, UtteranceEvent):
        row.end_ms = event.end_ms
        row.speaker = event.speaker
        row.text = event.text
        row.interrupted = event.interrupted
    elif isinstance(event, ToolCallEvent):
        row.end_ms = event.end_ms
        row.name = event.name
        row.status = event.status
        row.arguments = event.arguments
        row.result = event.result
    else:
        row.name = event.name
        row.detail = event.detail
    return row


def _event_from_row(row: CallEvent) -> TraceEvent:
    if row.type == CallEventType.UTTERANCE:
        if row.speaker is None:
            msg = f"utterance event {row.id} has no speaker"
            raise ValueError(msg)
        return UtteranceEvent(
            id=row.key,
            start_ms=row.start_ms,
            end_ms=row.end_ms,
            span_id=row.span_id,
            speaker=row.speaker,
            text=row.text or "",
            interrupted=row.interrupted,
        )
    if row.name is None:
        msg = f"{row.type} event {row.id} has no name"
        raise ValueError(msg)
    if row.type == CallEventType.TOOL_CALL:
        return ToolCallEvent(
            id=row.key,
            start_ms=row.start_ms,
            end_ms=row.end_ms,
            span_id=row.span_id,
            name=row.name,
            arguments=row.arguments,
            status=row.status,
            result=row.result,
        )
    return MarkerEvent(
        id=row.key,
        start_ms=row.start_ms,
        span_id=row.span_id,
        name=row.name,
        detail=row.detail,
    )


def _agent_ref(trace: Trace) -> str:
    for component in trace.components or []:
        if component.kind == "agent" and component.ref:
            return component.ref
    return ""


def _state(trace: Trace) -> tuple[str | None, str | None]:
    """The agent's version, and one fingerprint over the components every call has."""
    agent_version: str | None = None
    parts: dict[str, str] = {}
    for component in trace.components or []:
        if component.kind == "agent" and agent_version is None:
            agent_version = component.version
        if component.kind in STATE_KINDS and component.fingerprint:
            parts.setdefault(component.kind, component.fingerprint)
    return agent_version, combined_fingerprint(parts)


class StoredTrace(NamedTuple):
    call: Call
    created: bool


def store_trace(
    *,
    session: Session,
    trace: Trace,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    integration_id: uuid.UUID | None = None,
    raw: dict[str, object] | None = None,
) -> StoredTrace:
    """Store ``trace`` for an agent, replacing any trace already stored for that call.

    A call is identified by ``(external_id, agent_id)``. Storing the same call again
    replaces its events and components, so re-running a corrected mapping is safe.

    Safe to call concurrently for the same call: the call row is created with
    ``ON CONFLICT DO NOTHING`` and then locked, so one caller creates it and the
    others replace its trace in turn.

    Returns:
        The call, and whether this store created it.
    """
    inserted = session.execute(
        pg_insert(_CALL_TABLE)
        .values(
            id=uuid.uuid4(),
            company_id=company_id,
            agent_id=agent_id,
            integration_id=integration_id,
            provider=trace.provider,
            external_id=trace.external_id,
            provider_agent_id=_agent_ref(trace),
            started_at=_to_naive_utc(trace.started_at),
            source=trace.source,
        )
        .on_conflict_do_nothing(index_elements=["external_id", "agent_id"])
        .returning(_CALL_TABLE.c.id)
    ).first()
    created = inserted is not None

    call = session.exec(
        select(Call)
        .where(Call.external_id == trace.external_id, Call.agent_id == agent_id)
        .with_for_update()
    ).one()

    parties = trace.parties
    call.provider = trace.provider
    call.provider_agent_id = _agent_ref(trace) or call.provider_agent_id
    call.started_at = _to_naive_utc(trace.started_at)
    call.schema_version = trace.schema_version
    call.source = trace.source
    call.channel = trace.channel
    call.direction = trace.direction
    call.ended_at = _to_naive_utc(trace.ended_at) if trace.ended_at else None
    call.end_reason = trace.end_reason
    call.end_reason_detail = trace.end_reason_detail
    call.trace_id = trace.trace_id
    call.agent_number = parties.agent_number if parties else None
    call.caller_number = parties.caller_number if parties else None
    call.recording_url = trace.recording_url
    call.reports_tool_calls = trace.reports_tool_calls
    call.agent_version, call.state_fingerprint = _state(trace)
    call.inputs = trace.inputs
    call.outputs = trace.outputs
    call.extensions = trace.extensions
    if raw is not None:
        call.raw = dict(raw)
    session.add(call)
    session.flush()

    session.exec(delete(CallEvent).where(col(CallEvent.call_id) == call.id))
    session.exec(delete(CallComponent).where(col(CallComponent.call_id) == call.id))
    session.flush()

    for seq, event in enumerate(trace.events):
        session.add(
            _event_row(event, seq=seq, call_id=call.id, company_id=call.company_id)
        )
    for seq, component in enumerate(trace.components or []):
        session.add(
            CallComponent(
                company_id=call.company_id,
                call_id=call.id,
                seq=seq,
                kind=component.kind,
                name=component.name,
                ref=component.ref,
                version=component.version,
                fingerprint=component.fingerprint,
            )
        )
    session.commit()
    session.refresh(call)
    return StoredTrace(call=call, created=created)


def get_trace(*, session: Session, call: Call) -> Trace | None:
    """Assemble the trace stored for ``call``; ``None`` when it has none."""
    if call.schema_version is None:
        return None

    event_rows = session.exec(
        select(CallEvent)
        .where(CallEvent.call_id == call.id)
        .order_by(col(CallEvent.seq))
    ).all()
    component_rows = session.exec(
        select(CallComponent)
        .where(CallComponent.call_id == call.id)
        .order_by(col(CallComponent.seq))
    ).all()

    parties: TraceParties | None = None
    if call.agent_number is not None or call.caller_number is not None:
        parties = TraceParties(
            agent_number=call.agent_number, caller_number=call.caller_number
        )

    return Trace(
        provider=call.provider,
        external_id=call.external_id,
        started_at=_to_aware_utc(call.started_at),
        source=call.source,
        channel=call.channel,
        direction=call.direction,
        ended_at=_to_aware_utc(call.ended_at) if call.ended_at else None,
        end_reason=call.end_reason,
        end_reason_detail=call.end_reason_detail,
        trace_id=call.trace_id,
        parties=parties,
        recording_url=call.recording_url,
        inputs=call.inputs,
        components=[
            TraceComponent(
                kind=row.kind,
                name=row.name,
                ref=row.ref,
                version=row.version,
                fingerprint=row.fingerprint,
            )
            for row in component_rows
        ]
        or None,
        reports_tool_calls=call.reports_tool_calls,
        events=[_event_from_row(row) for row in event_rows],
        outputs=call.outputs,
        extensions=call.extensions,
    )
