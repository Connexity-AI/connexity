"""Latency, measured from each call's own turns (plan `plans/2026-11-14-agent-page.md`).

A basic first measure, to be made more useful later (Dmytro, 2026-11-14). It works the
same for every provider:

- a **reply gap** is the time from the end of a caller's turn to the start of the
  agent's next turn. An agent turn that starts before the caller has finished (talking
  over, or "yeah" while the agent speaks) is not a gap;
- a **call's latency** is the median of its reply gaps; a call without one has none;
- an **agent's latency** for a period is the average of its calls' latencies.

See `docs-internal/metrics.md`.
"""

import statistics
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import NamedTuple

from sqlmodel import Session, col, select

from app.models.call import Call, CallEvent
from app.models.enums import CallEventType, Speaker


def reply_gaps(turns: list[tuple[Speaker | None, int | None, int | None]]) -> list[int]:
    """The reply gaps, in ms, of one call's turns given in order as (speaker, start,
    end)."""
    gaps: list[int] = []
    caller_end: int | None = None
    for speaker, start, end in turns:
        if speaker is Speaker.CALLER and end is not None:
            caller_end = end
        elif speaker is Speaker.AGENT and start is not None:
            if caller_end is not None and start >= caller_end:
                gaps.append(start - caller_end)
            caller_end = None
        else:
            # Someone else spoke (after a transfer): the agent is not answering the
            # caller's last words.
            caller_end = None
    return gaps


def call_latency(
    turns: list[tuple[Speaker | None, int | None, int | None]],
) -> float | None:
    """A call's latency in seconds: the median of its reply gaps."""
    gaps = reply_gaps(turns)
    return round(statistics.median(gaps) / 1000, 3) if gaps else None


class CallLatency(NamedTuple):
    call_id: uuid.UUID
    agent_id: uuid.UUID
    day: date
    seconds: float


def call_latencies(
    *, session: Session, agent_ids: list[uuid.UUID], since: datetime
) -> list[CallLatency]:
    """The latency of every call of these agents that started since ``since`` and has
    one."""
    if not agent_ids:
        return []
    rows = session.exec(
        select(
            Call.id,
            Call.agent_id,
            Call.started_at,
            CallEvent.speaker,
            CallEvent.start_ms,
            CallEvent.end_ms,
        )
        .join(CallEvent, col(CallEvent.call_id) == col(Call.id))
        .where(
            col(Call.agent_id).in_(agent_ids),
            col(Call.deleted_at).is_(None),
            col(Call.started_at) >= since.astimezone(UTC).replace(tzinfo=None),
            CallEvent.type == CallEventType.UTTERANCE,
        )
        .order_by(col(Call.id), col(CallEvent.start_ms), col(CallEvent.seq))
    ).all()
    turns: dict[uuid.UUID, list[tuple[Speaker | None, int | None, int | None]]] = (
        defaultdict(list)
    )
    meta: dict[uuid.UUID, tuple[uuid.UUID, date]] = {}
    for call_id, agent_id, started, speaker, start, end in rows:
        turns[call_id].append((speaker, start, end))
        meta[call_id] = (agent_id, started.date())
    out = []
    for call_id, call_turns in turns.items():
        seconds = call_latency(call_turns)
        if seconds is not None:
            agent_id, day = meta[call_id]
            out.append(CallLatency(call_id, agent_id, day, seconds))
    return out


def average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def agent_latencies(
    *, session: Session, agent_ids: list[uuid.UUID], since: datetime
) -> dict[uuid.UUID, float]:
    """Each agent's latency in seconds for the period, for agents with any."""
    per_agent: dict[uuid.UUID, list[float]] = defaultdict(list)
    for row in call_latencies(session=session, agent_ids=agent_ids, since=since):
        per_agent[row.agent_id].append(row.seconds)
    return {
        agent_id: value
        for agent_id, values in per_agent.items()
        if (value := average(values)) is not None
    }
