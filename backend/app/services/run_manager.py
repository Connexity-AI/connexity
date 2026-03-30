import asyncio
import logging
import uuid
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RunEvent(BaseModel):
    event: str
    data: dict[str, Any]


class RunProgress(BaseModel):
    total_scenarios: int = 0
    completed_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0


SSE_KEEPALIVE_SECONDS = 15


class RunState:
    def __init__(self, run_id: uuid.UUID) -> None:
        self.run_id = run_id
        self.cancel_event = asyncio.Event()
        self.subscribers: list[asyncio.Queue[RunEvent]] = []
        self.progress = RunProgress()
        self.progress_lock = asyncio.Lock()
        self.event_log: list[RunEvent] = []
        self.task: asyncio.Task[Any] | None = None


class RunManager:
    def __init__(self) -> None:
        self._runs: dict[uuid.UUID, RunState] = {}

    def register(self, run_id: uuid.UUID) -> RunState:
        if run_id in self._runs:
            return self._runs[run_id]
        state = RunState(run_id)
        self._runs[run_id] = state
        return state

    def unregister(self, run_id: uuid.UUID) -> None:
        if run_id in self._runs:
            state = self._runs.pop(run_id)
            # Notify any remaining subscribers that the stream is closing
            close_event = RunEvent(event="stream_closed", data={})
            for queue in state.subscribers:
                queue.put_nowait(close_event)

    def is_active(self, run_id: uuid.UUID) -> bool:
        return run_id in self._runs

    def get_state(self, run_id: uuid.UUID) -> RunState | None:
        return self._runs.get(run_id)

    def get_progress(self, run_id: uuid.UUID) -> RunProgress | None:
        state = self._runs.get(run_id)
        if state:
            return state.progress
        return None

    def emit(self, run_id: uuid.UUID, event_name: str, data: dict[str, Any]) -> None:
        state = self._runs.get(run_id)
        if not state:
            return

        event = RunEvent(event=event_name, data=data)
        state.event_log.append(event)

        for queue in state.subscribers:
            queue.put_nowait(event)

    def signal_cancel(self, run_id: uuid.UUID) -> None:
        state = self._runs.get(run_id)
        if state:
            state.cancel_event.set()

    async def subscribe(self, run_id: uuid.UUID):
        state = self._runs.get(run_id)
        if not state:
            # If the run is not active, we just yield a single stream_closed event
            # The caller should handle fetching the final state from the DB
            yield RunEvent(event="stream_closed", data={})
            return

        queue: asyncio.Queue[RunEvent] = asyncio.Queue()
        state.subscribers.append(queue)

        try:
            # Replay history
            for event in state.event_log:
                yield event

            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=SSE_KEEPALIVE_SECONDS
                    )
                except TimeoutError:
                    yield RunEvent(event="keepalive", data={})
                    continue
                yield event
                if event.event == "stream_closed":
                    break
        finally:
            if queue in state.subscribers:
                state.subscribers.remove(queue)


run_manager = RunManager()
