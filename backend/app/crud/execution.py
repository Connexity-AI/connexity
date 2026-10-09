"""Storing and reading the executions tied to a call's tool calls."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Session, col, delete, select

from app.models.call import Call
from app.models.execution import (
    CallExecution,
    CallExecutionStep,
    Execution,
    ExecutionStep,
)


def _to_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.astimezone(UTC).replace(tzinfo=None)


def _to_aware_utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=UTC) if value is not None else None


def replace_executions(
    *,
    session: Session,
    call: Call,
    executions: list[Execution],
    integration_ids: dict[str, uuid.UUID] | None = None,
) -> None:
    """Store ``executions`` for the tool calls they name, replacing what those had.

    Only the named tool calls are touched: an execution stored earlier for another tool
    call of the same call stays. ``integration_ids`` maps an execution's ``event_id`` to
    the connection it was read from.
    """
    event_keys = [execution.event_id for execution in executions]
    if not event_keys:
        return
    session.exec(
        delete(CallExecution).where(
            col(CallExecution.call_id) == call.id,
            col(CallExecution.event_key).in_(event_keys),
        )
    )
    session.flush()
    for execution in executions:
        row = CallExecution(
            company_id=call.company_id,
            call_id=call.id,
            event_key=execution.event_id,
            integration_id=(integration_ids or {}).get(execution.event_id),
            provider=execution.provider,
            external_id=execution.external_id,
            workflow_id=execution.workflow_id,
            workflow_name=execution.workflow_name,
            workflow_version=execution.workflow_version,
            status=execution.status,
            started_at=_to_naive_utc(execution.started_at),
            ended_at=_to_naive_utc(execution.ended_at),
            match=execution.match,
        )
        session.add(row)
        for seq, step in enumerate(execution.steps):
            session.add(
                CallExecutionStep(
                    company_id=call.company_id,
                    execution_id=row.id,
                    seq=seq,
                    name=step.name,
                    kind=step.kind,
                    status=step.status,
                    started_at=_to_naive_utc(step.started_at),
                    duration_ms=step.duration_ms,
                    input_from=step.input_from or None,
                    output=step.output,
                    error=step.error,
                    data_dropped=step.data_dropped,
                )
            )
    session.commit()


def get_executions(*, session: Session, call: Call) -> list[Execution]:
    """The executions stored for ``call``, in the order they started."""
    rows = session.exec(
        select(CallExecution)
        .where(CallExecution.call_id == call.id)
        .order_by(col(CallExecution.started_at), col(CallExecution.event_key))
    ).all()
    if not rows:
        return []
    steps_by_execution: dict[uuid.UUID, list[CallExecutionStep]] = {}
    for step in session.exec(
        select(CallExecutionStep)
        .where(col(CallExecutionStep.execution_id).in_([row.id for row in rows]))
        .order_by(col(CallExecutionStep.execution_id), col(CallExecutionStep.seq))
    ).all():
        steps_by_execution.setdefault(step.execution_id, []).append(step)
    return [
        Execution(
            event_id=row.event_key,
            provider=row.provider,
            external_id=row.external_id,
            workflow_id=row.workflow_id,
            workflow_name=row.workflow_name,
            workflow_version=row.workflow_version,
            status=row.status,
            started_at=_to_aware_utc(row.started_at),
            ended_at=_to_aware_utc(row.ended_at),
            match=row.match,
            steps=[
                ExecutionStep(
                    name=step.name,
                    kind=step.kind,
                    status=step.status,
                    started_at=_to_aware_utc(step.started_at),
                    duration_ms=step.duration_ms,
                    input_from=step.input_from or [],
                    output=step.output,
                    error=step.error,
                    data_dropped=step.data_dropped,
                )
                for step in steps_by_execution.get(row.id, [])
            ],
        )
        for row in rows
    ]
