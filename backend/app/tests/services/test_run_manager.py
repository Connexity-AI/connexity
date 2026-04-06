"""Tests for the in-memory RunManager: registration, events, SSE pub/sub, cancellation."""

import asyncio
import uuid

import pytest

from app.services.run_manager import RunEvent, RunManager, RunProgress


@pytest.fixture()
def manager() -> RunManager:
    return RunManager()


def test_register_creates_state(manager: RunManager) -> None:
    run_id = uuid.uuid4()
    state = manager.register(run_id)
    assert state.run_id == run_id
    assert manager.is_active(run_id)
    assert isinstance(state.progress, RunProgress)
    assert state.progress.total_test_cases == 0


def test_register_idempotent(manager: RunManager) -> None:
    run_id = uuid.uuid4()
    s1 = manager.register(run_id)
    s2 = manager.register(run_id)
    assert s1 is s2


def test_unregister_removes_state(manager: RunManager) -> None:
    run_id = uuid.uuid4()
    manager.register(run_id)
    manager.unregister(run_id)
    assert not manager.is_active(run_id)


def test_unregister_nonexistent_is_noop(manager: RunManager) -> None:
    manager.unregister(uuid.uuid4())


def test_is_active_false_for_unknown(manager: RunManager) -> None:
    assert not manager.is_active(uuid.uuid4())


def test_get_progress_returns_none_for_unknown(manager: RunManager) -> None:
    assert manager.get_progress(uuid.uuid4()) is None


def test_get_progress_returns_state_progress(manager: RunManager) -> None:
    run_id = uuid.uuid4()
    state = manager.register(run_id)
    state.progress.total_test_cases = 5
    state.progress.completed_count = 3
    progress = manager.get_progress(run_id)
    assert progress is not None
    assert progress.total_test_cases == 5
    assert progress.completed_count == 3


def test_emit_appends_to_event_log(manager: RunManager) -> None:
    run_id = uuid.uuid4()
    manager.register(run_id)
    manager.emit(run_id, "run_started", {"run_id": str(run_id)})
    state = manager._runs[run_id]
    assert len(state.event_log) == 1
    assert state.event_log[0].event == "run_started"


def test_emit_to_unknown_run_is_noop(manager: RunManager) -> None:
    manager.emit(uuid.uuid4(), "run_started", {})


def test_signal_cancel_sets_event(manager: RunManager) -> None:
    run_id = uuid.uuid4()
    state = manager.register(run_id)
    assert not state.cancel_event.is_set()
    manager.signal_cancel(run_id)
    assert state.cancel_event.is_set()


def test_signal_cancel_unknown_is_noop(manager: RunManager) -> None:
    manager.signal_cancel(uuid.uuid4())


async def test_emit_delivers_to_subscriber(manager: RunManager) -> None:
    run_id = uuid.uuid4()
    manager.register(run_id)

    received: list[RunEvent] = []

    async def consume():
        async for event in manager.subscribe(run_id):
            received.append(event)
            if event.event == "stream_closed":
                break

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)

    manager.emit(run_id, "test_case_started", {"idx": 1})
    manager.unregister(run_id)
    await task

    event_names = [e.event for e in received]
    assert "test_case_started" in event_names
    assert event_names[-1] == "stream_closed"


async def test_subscribe_replays_history(manager: RunManager) -> None:
    run_id = uuid.uuid4()
    manager.register(run_id)
    manager.emit(run_id, "run_started", {"t": 1})
    manager.emit(run_id, "test_case_completed", {"t": 2})

    received: list[RunEvent] = []

    async def consume():
        async for event in manager.subscribe(run_id):
            received.append(event)
            if event.event == "stream_closed":
                break

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    manager.unregister(run_id)
    await task

    assert received[0].event == "run_started"
    assert received[1].event == "test_case_completed"
    assert received[-1].event == "stream_closed"


async def test_subscribe_unknown_run_yields_closed(manager: RunManager) -> None:
    received: list[RunEvent] = []
    async for event in manager.subscribe(uuid.uuid4()):
        received.append(event)
    assert len(received) == 1
    assert received[0].event == "stream_closed"


async def test_unregister_notifies_multiple_subscribers(manager: RunManager) -> None:
    run_id = uuid.uuid4()
    manager.register(run_id)

    results: list[list[RunEvent]] = [[], []]

    async def consume(idx: int):
        async for event in manager.subscribe(run_id):
            results[idx].append(event)
            if event.event == "stream_closed":
                break

    t1 = asyncio.create_task(consume(0))
    t2 = asyncio.create_task(consume(1))
    await asyncio.sleep(0.01)

    manager.unregister(run_id)
    await asyncio.gather(t1, t2)

    for events in results:
        assert events[-1].event == "stream_closed"


async def test_subscriber_cleanup_on_generator_exit(manager: RunManager) -> None:
    run_id = uuid.uuid4()
    state = manager.register(run_id)

    manager.emit(run_id, "run_started", {"x": 1})

    gen = manager.subscribe(run_id)
    event = await gen.__anext__()
    assert event.event == "run_started"

    await gen.aclose()

    assert len(state.subscribers) == 0
