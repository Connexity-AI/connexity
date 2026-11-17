"""Which tool calls book an appointment, read from the tool's name.

Rules must work on any agent, so they cannot name an agent's tools. A tool that books
says so in its name; one that only looks (availability, slots) or changes a booking
(cancel, reschedule) does not count (Dmytro accepted, 2026-11-13). A tool whose name says
nothing about what it does is not recognised, so the rules find nothing on it rather
than something wrong.
"""

import re

from app.models.trace import ToolCallEvent, Trace

_BOOKS = re.compile(r"book|schedul|appointment|reserv", re.IGNORECASE)
_NOT_BOOKING = re.compile(
    r"availab|slot|get_|list|find|check|search|cancel|reschedul", re.IGNORECASE
)


def is_booking_tool(name: str) -> bool:
    return bool(_BOOKS.search(name)) and not _NOT_BOOKING.search(name)


def booking_calls(trace: Trace) -> list[ToolCallEvent]:
    """The trace's calls to booking tools, in the order they happened."""
    return [
        event
        for event in trace.events
        if isinstance(event, ToolCallEvent) and is_booking_tool(event.name)
    ]
