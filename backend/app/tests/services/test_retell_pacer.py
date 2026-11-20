"""Requests to Retell's playground are paced to its limit, 8 per 2 seconds per
organization (plan `plans/2026-11-20-test-run-progress-and-speed.md`)."""

import asyncio
from unittest.mock import patch

from app.services import retell
from app.services.retell import RequestPacer


class _Clock:
    """Time that only moves when something sleeps."""

    def __init__(self) -> None:
        self.now = 100.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _started(pacer: RequestPacer, clock: _Clock, keys: list[str]) -> list[float]:
    """When each request was let through, with every request arriving at once."""

    async def run() -> list[float]:
        out: list[float] = []

        async def one(key: str) -> None:
            await pacer.wait(key)
            out.append(clock.now)

        await asyncio.gather(*(one(key) for key in keys))
        return out

    with (
        patch.object(retell.time, "monotonic", clock.monotonic),
        patch.object(retell.asyncio, "sleep", clock.sleep),
    ):
        return asyncio.run(run())


def test_25_calls_starting_at_once_go_out_8_every_2_seconds() -> None:
    clock = _Clock()
    pacer = RequestPacer(limit=8, window=2.0)

    started = sorted(_started(pacer, clock, ["org"] * 25))

    assert started[:8] == [100.0] * 8
    assert started[8:16] == [102.0] * 8
    assert started[16:24] == [104.0] * 8
    assert started[24] == 106.0
    # Never more than 8 inside any 2 seconds.
    for at in started:
        assert sum(1 for other in started if at <= other < at + 2.0) <= 8


def test_each_retell_organization_has_its_own_limit() -> None:
    clock = _Clock()
    pacer = RequestPacer(limit=8, window=2.0)

    started = _started(pacer, clock, ["org-a"] * 8 + ["org-b"] * 8)

    assert started == [100.0] * 16
    assert clock.slept == []


def test_a_pacer_turned_off_never_waits() -> None:
    clock = _Clock()
    pacer = RequestPacer(limit=1, window=2.0)
    pacer.enabled = False

    assert _started(pacer, clock, ["org"] * 5) == [100.0] * 5
