"""Latency, measured from each call's own turns, the same way for every provider
(plans `plans/2026-11-14-agent-page.md`, `plans/2026-11-19-agents-latency-versions.md`):

- a **reply gap** is the time from the end of a caller's turn to the start of the
  agent's next turn. An agent turn that starts before the caller has finished (talking
  over, or "yeah" while the agent speaks) is not a gap;
- **latency** is p50 and p95 over every reply gap in the period: every time the agent
  answered the caller (Dmytro, 2026-11-18 for the Dashboard, 2026-11-19 for the Agents
  list and the agent page).

See `docs-internal/metrics.md`.
"""

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


class CallGaps(NamedTuple):
    call_id: uuid.UUID
    agent_id: uuid.UUID
    day: date
    gaps: list[int]


def _turns(
    *,
    session: Session,
    agent_ids: list[uuid.UUID],
    since: datetime,
    until: datetime | None = None,
) -> tuple[
    dict[uuid.UUID, list[tuple[Speaker | None, int | None, int | None]]],
    dict[uuid.UUID, tuple[uuid.UUID, date]],
]:
    """Each call's turns in order, and its agent and day, for calls of these agents
    that started in ``[since, until)``."""
    if not agent_ids:
        return {}, {}
    window = [col(Call.started_at) >= since.astimezone(UTC).replace(tzinfo=None)]
    if until is not None:
        window.append(col(Call.started_at) < until.astimezone(UTC).replace(tzinfo=None))
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
            *window,
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
    return turns, meta


def call_gaps(
    *, session: Session, agent_ids: list[uuid.UUID], since: datetime
) -> list[CallGaps]:
    """The reply gaps of every call of these agents that started since ``since`` and
    has one."""
    turns, meta = _turns(session=session, agent_ids=agent_ids, since=since)
    out = []
    for call_id, call_turns in turns.items():
        gaps = reply_gaps(call_turns)
        if gaps:
            agent_id, day = meta[call_id]
            out.append(CallGaps(call_id, agent_id, day, gaps))
    return out


class GapPercentiles(NamedTuple):
    p50: float | None
    p95: float | None
    # How many reply gaps they rest on.
    answers: int


def percentile(values: list[int], share: float) -> float:
    """The nearest-rank percentile of ``values`` (in ms), in seconds."""
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * share // 1))  # ceil, at least the first
    return round(ordered[int(rank) - 1] / 1000, 2)


def gap_percentiles(gaps: list[int]) -> "GapPercentiles":
    """p50 and p95, in seconds, over these reply gaps (in ms)."""
    if not gaps:
        return GapPercentiles(None, None, 0)
    return GapPercentiles(percentile(gaps, 0.5), percentile(gaps, 0.95), len(gaps))


def agent_gap_percentiles(
    *, session: Session, agent_ids: list[uuid.UUID], since: datetime
) -> dict[uuid.UUID, "GapPercentiles"]:
    """Each agent's p50 and p95 over its reply gaps since ``since``, in one pass, for
    agents with any."""
    per_agent: dict[uuid.UUID, list[int]] = defaultdict(list)
    for row in call_gaps(session=session, agent_ids=agent_ids, since=since):
        per_agent[row.agent_id].extend(row.gaps)
    return {agent_id: gap_percentiles(gaps) for agent_id, gaps in per_agent.items()}


def reply_gap_percentiles(
    *,
    session: Session,
    agent_ids: list[uuid.UUID],
    since: datetime,
    until: datetime | None = None,
) -> GapPercentiles:
    """p50 and p95, in seconds, over every reply gap of these agents' calls in the
    window: every time an agent answered the caller (Dmytro, 2026-11-18)."""
    turns, _ = _turns(session=session, agent_ids=agent_ids, since=since, until=until)
    return gap_percentiles(
        [gap for call_turns in turns.values() for gap in reply_gaps(call_turns)]
    )
