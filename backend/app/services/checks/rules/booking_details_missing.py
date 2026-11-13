"""A booking made with an empty or placeholder name, street address or zip.

Found by a rule (deterministic): it reads the booking tool's arguments. See
`docs-internal/issue-types.md`.
"""

import re

from pydantic import JsonValue

from app.models.enums import CheckMode, TraceCapability
from app.services.checks.base import CheckInput, Raised, RuleCheck
from app.services.checks.rules.booking_tools import booking_calls

# Arguments that hold who and where the booking is for.
_DETAIL = re.compile(r"name|address|street|zip|postal", re.IGNORECASE)
_PLACEHOLDER = re.compile(
    r"\{\{.*\}\}"  # a template variable left unfilled
    r"|^\s*\[.*\]\s*$"  # a bracketed note: [address pending]
    r"|^\s*0{4,}\s*$"  # a run of zeros: 00000
    r"|\b(missing|pending|unknown|tbd|n/?a|none|null|placeholder)\b",
    re.IGNORECASE,
)


def _is_missing(value: JsonValue) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return not value.strip() or bool(_PLACEHOLDER.search(value))


def _run(check_input: CheckInput) -> list[Raised]:
    found = []
    for event in booking_calls(check_input.trace):
        missing = sorted(
            name
            for name, value in (event.arguments or {}).items()
            if _DETAIL.search(name) and _is_missing(value)
        )
        if missing:
            # The argument names only: never their values.
            found.append(
                Raised(event_ids=(event.id,), key=event.name, detail={"empty": missing})
            )
    return found


BOOKING_DETAILS_MISSING = RuleCheck(
    type="booking_details_missing",
    version=1,
    title="Booking with missing or placeholder details",
    description=(
        "A booking tool was called with an empty or placeholder name, street address "
        "or zip."
    ),
    default_mode=CheckMode.FAILS,
    category="booking",
    run=_run,
    needs=(TraceCapability.TOOL_CALLS,),
)
