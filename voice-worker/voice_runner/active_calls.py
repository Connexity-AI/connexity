"""In-process coordination between the outbound dial worker and `/ws`.

Twilio callbacks run on FastAPI concurrently with the blocking worker loop, so we
coordinate through asyncio primitives instead of holding a mutex across awaits.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ActiveCall:
    job_id: uuid.UUID
    call_sid: str


class StreamReadyRegistry:
    """Wait until Twilio sends the media `start` frame for this job."""

    def __init__(self) -> None:
        self._events: dict[uuid.UUID, asyncio.Event] = {}

    def register(self, job_id: uuid.UUID) -> asyncio.Event:
        ev = asyncio.Event()
        self._events[job_id] = ev
        return ev

    def notify(self, job_id: uuid.UUID) -> None:
        ev = self._events.pop(job_id, None)
        if ev is not None:
            ev.set()

    def forget(self, job_id: uuid.UUID) -> None:
        self._events.pop(job_id, None)


class CallCompletionRegistry:
    """Dial side waits for the websocket session to finish the Pipecat pipeline."""

    def __init__(self) -> None:
        self._futures: dict[uuid.UUID, asyncio.Future[Any]] = {}

    def register(self, job_id: uuid.UUID, fut: asyncio.Future[Any]) -> None:
        self._futures[job_id] = fut

    def cancel(self, job_id: uuid.UUID) -> None:
        fut = self._futures.pop(job_id, None)
        if fut is not None and not fut.done():
            fut.cancel()

    def resolve(self, job_id: uuid.UUID, exc: BaseException | None = None) -> None:
        fut = self._futures.pop(job_id, None)
        if fut is None or fut.done():
            return
        if exc is None:
            fut.set_result(None)
        else:
            fut.set_exception(exc)


STREAM_REGISTRY = StreamReadyRegistry()
CALL_COMPLETION = CallCompletionRegistry()

# Only this job_id may open `/ws` while a dial is in flight (best-effort guard).
EXPECTED_JOB_ID: uuid.UUID | None = None

# In-flight Twilio call for graceful shutdown (one call per worker process).
ACTIVE_CALL: ActiveCall | None = None


def register_active_call(*, job_id: uuid.UUID, call_sid: str) -> None:
    global ACTIVE_CALL
    ACTIVE_CALL = ActiveCall(job_id=job_id, call_sid=call_sid)


def clear_active_call() -> None:
    global ACTIVE_CALL
    ACTIVE_CALL = None


def get_active_call() -> ActiveCall | None:
    return ACTIVE_CALL
