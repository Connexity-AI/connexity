"""The same slot booked twice in one call.

Found by a rule (deterministic): it compares the booking tool's calls and their time
argument. See `docs-internal/issue-types.md`.
"""

from pydantic import JsonValue

from app.models.enums import CheckMode, ToolCallStatus, TraceCapability
from app.models.trace import ToolCallEvent
from app.services.checks.base import CheckInput, Raised, RuleCheck
from app.services.checks.rules.booking_tools import booking_calls

_FAILED = (ToolCallStatus.ERROR, ToolCallStatus.TIMEOUT)
# The argument that holds when, most specific first. "timeZone" is not a time.
_TIME_WORDS = ("start", "slot", "datetime", "time", "date")


def _when(event: ToolCallEvent) -> JsonValue:
    arguments = event.arguments or {}
    for word in _TIME_WORDS:
        for name, value in arguments.items():
            lowered = name.lower()
            if word in lowered and "zone" not in lowered and value not in (None, ""):
                return value
    return None


def _run(check_input: CheckInput) -> list[Raised]:
    seen: dict[tuple[str, str], str] = {}
    found = []
    for event in booking_calls(check_input.trace):
        if event.status in _FAILED:
            continue
        when = _when(event)
        if when is None:
            continue
        slot = (event.name, str(when))
        if slot in seen:
            found.append(
                Raised(
                    event_ids=(seen[slot], event.id),
                    key=event.name,
                    detail={"bookings": 2},
                )
            )
        else:
            seen[slot] = event.id
    return found


BOOKING_DUPLICATED = RuleCheck(
    type="booking_duplicated",
    version=1,
    title="Two bookings for one slot",
    description="A booking tool was called twice in one call for the same time.",
    default_mode=CheckMode.FAILS,
    category="booking",
    run=_run,
    needs=(TraceCapability.TOOL_CALLS,),
)
