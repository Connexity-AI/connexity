"""Find what the backend did for a call's tool calls, and store it.

For each tool call whose tool is mapped to a workflow, the mapped n8n is asked for that
workflow's executions that started during the call. An execution belongs to a tool call
when its trigger carries the call's id, the tool's name and the same arguments.

Nothing here raises for a backend problem: a call is stored whether or not its
executions can be read. Problems are returned and logged, without call content.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, col, select

from app import crud
from app.core.db import engine
from app.core.encryption import decrypt
from app.models.call import Call, CallEvent
from app.models.enums import CallEventType, ExecutionMatch
from app.models.execution import Execution, ExecutionSyncResult
from app.models.integration import AgentToolBackend, Integration
from app.services.mappings.n8n import (
    N8nMappingError,
    ToolRequest,
    n8n_execution_to_execution,
    n8n_tool_request,
)
from app.services.n8n import N8nError, get_n8n_execution, list_n8n_executions

logger = logging.getLogger(__name__)

# The backend's clock and the voice provider's are not the same clock.
_WINDOW_SLACK = timedelta(seconds=30)
# A call with no recorded end is searched this far past its start.
_OPEN_CALL_WINDOW = timedelta(hours=2)
# Executions of one workflow read for one call. A call cannot have made more tool calls
# than this, so more means the time filter was ignored.
_MAX_EXECUTIONS_PER_WORKFLOW = 500
_MAX_DETAILS_PER_WORKFLOW = 100
# A guess must start this close to the tool call.
_GUESS_TOLERANCE = timedelta(seconds=10)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _event_time(call: Call, event: CallEvent) -> datetime | None:
    if event.start_ms is None:
        return None
    return _aware(call.started_at) + timedelta(milliseconds=event.start_ms)


def _distance(
    call: Call, event: CallEvent, started_at: datetime | None
) -> timedelta | None:
    at = _event_time(call, event)
    if at is None or started_at is None:
        return None
    return abs(started_at - at)


def _distance_or_far(
    call: Call, event: CallEvent, started_at: datetime | None
) -> timedelta:
    distance = _distance(call, event, started_at)
    return timedelta.max if distance is None else distance


def _pick(
    call: Call,
    request: ToolRequest,
    started_at: datetime | None,
    events: list[CallEvent],
    taken: set[str],
) -> tuple[CallEvent, ExecutionMatch] | None:
    """The tool call an execution belongs to, among one tool's calls on one call."""
    free = [
        event
        for event in events
        if event.key not in taken
        and (request.tool_name is None or event.name == request.tool_name)
    ]
    same_arguments = [
        event for event in free if (event.arguments or {}) == (request.arguments or {})
    ]
    if request.call_id is not None:
        if request.call_id != call.external_id:
            return None
        if not same_arguments:
            return None
        # The same tool called twice with the same arguments: the nearest in time.
        nearest = min(
            same_arguments, key=lambda event: _distance_or_far(call, event, started_at)
        )
        return nearest, ExecutionMatch.EXACT

    # No call id in the trigger. Arguments and time are all there is.
    close = [
        (distance, event)
        for event in same_arguments
        if (distance := _distance(call, event, started_at)) is not None
        and distance <= _GUESS_TOLERANCE
    ]
    if not close:
        return None
    return min(close, key=lambda entry: entry[0])[1], ExecutionMatch.GUESS


async def _executions_for_workflow(
    *,
    call: Call,
    integration: Integration,
    workflow_id: str,
    events: list[CallEvent],
) -> tuple[list[Execution], list[str]]:
    api_key = decrypt(integration.encrypted_api_key)
    base_url = integration.base_url or ""
    started = _aware(call.started_at)
    ended = _aware(call.ended_at) if call.ended_at else started + _OPEN_CALL_WINDOW
    problems: list[str] = []
    try:
        summaries = await list_n8n_executions(
            base_url,
            api_key,
            workflow_id=workflow_id,
            started_after=started - _WINDOW_SLACK,
            started_before=ended + _WINDOW_SLACK,
            max_items=_MAX_EXECUTIONS_PER_WORKFLOW,
        )
    except N8nError as exc:
        return [], [f"{integration.name}: {exc}"]
    if len(summaries) > _MAX_DETAILS_PER_WORKFLOW:
        problems.append(
            f"{integration.name}: too many executions in the call's window; "
            f"only the first {_MAX_DETAILS_PER_WORKFLOW} were read"
        )
        summaries = summaries[:_MAX_DETAILS_PER_WORKFLOW]

    found: list[Execution] = []
    taken: set[str] = set()
    # Oldest first, so that identical tool calls are paired in the order they happened.
    for summary in sorted(
        summaries, key=lambda item: item.started_at or datetime.max.replace(tzinfo=UTC)
    ):
        try:
            payload: dict[str, Any] = await get_n8n_execution(
                base_url, api_key, summary.id
            )
        except N8nError as exc:
            problems.append(f"{integration.name}: {exc}")
            continue
        request = n8n_tool_request(payload)
        if request is None:
            continue
        picked = _pick(call, request, summary.started_at, events, taken)
        if picked is None:
            continue
        event, match = picked
        try:
            found.append(
                n8n_execution_to_execution(payload, event_id=event.key, match=match)
            )
        except N8nMappingError as exc:
            problems.append(f"{integration.name}: {exc}")
            continue
        taken.add(event.key)
    return found, problems


async def sync_call_executions(*, session: Session, call: Call) -> ExecutionSyncResult:
    """Look for the executions behind ``call``'s tool calls and store those found."""
    events = list(
        session.exec(
            select(CallEvent)
            .where(
                CallEvent.call_id == call.id,
                CallEvent.type == CallEventType.TOOL_CALL,
            )
            .order_by(col(CallEvent.seq))
        ).all()
    )
    result = ExecutionSyncResult(tool_calls=len(events), mapped=0, matched=0)
    if not events:
        return result

    backends = {
        backend.tool_name: (backend, integration)
        for backend, integration in crud.list_tool_backends(
            session=session, agent_id=call.agent_id
        )
    }
    groups: dict[
        tuple[uuid.UUID, str], tuple[AgentToolBackend, Integration, list[CallEvent]]
    ] = {}
    for event in events:
        mapped = backends.get(event.name or "")
        if mapped is None:
            continue
        backend, integration = mapped
        result.mapped += 1
        groups.setdefault(
            (integration.id, backend.workflow_id), (backend, integration, [])
        )[2].append(event)

    for backend, integration, group_events in groups.values():
        executions, problems = await _executions_for_workflow(
            call=call,
            integration=integration,
            workflow_id=backend.workflow_id,
            events=group_events,
        )
        result.problems.extend(problems)
        if executions:
            crud.replace_executions(
                session=session,
                call=call,
                executions=executions,
                integration_ids={
                    execution.event_id: integration.id for execution in executions
                },
            )
            result.matched += len(executions)

    if result.problems:
        logger.warning(
            "Executions for call %s: %d problem(s): %s",
            call.id,
            len(result.problems),
            "; ".join(sorted(set(result.problems))),
        )
    return result


async def sync_call_executions_safely(
    *, session: Session, call: Call
) -> ExecutionSyncResult | None:
    """As ``sync_call_executions``, but never raises: storing a call must not fail
    because its backend could not be read."""
    try:
        return await sync_call_executions(session=session, call=call)
    except Exception:  # noqa: BLE001 - the call is already stored; log and move on
        session.rollback()
        logger.exception("Executions for call %s could not be read", call.id)
        return None


async def sync_call_executions_in_background(call_id: uuid.UUID) -> None:
    """For use after a response has been sent: its own database session, never raises."""
    with Session(engine) as session:
        call = session.get(Call, call_id)
        if call is not None:
            await sync_call_executions_safely(session=session, call=call)
