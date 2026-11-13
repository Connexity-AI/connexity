"""The two booking checks, on invented Retell calls. Both are rules (deterministic)."""

import json
from typing import Any

import pytest

from app.models.enums import CheckKind, CheckMode
from app.services.checks.base import CheckInput, Raised
from app.services.checks.rules.booking_details_missing import BOOKING_DETAILS_MISSING
from app.services.checks.rules.booking_duplicated import BOOKING_DUPLICATED
from app.services.checks.rules.booking_tools import is_booking_tool
from app.services.mappings.retell import retell_call_to_trace
from app.tests.utils.retell_payloads import invocation, result, retell_call, speech

FULL = {
    "full_name": "Sam Example",
    "streetAddress": "1 Invented Road",
    "postalCode": "07700",
    "phone": "{{from_number}}",
    "timeZone": "America/New_York",
    "startTime": "2026-10-23T12:00:00-04:00",
}


def _tool(
    n: int, name: str, args: dict[str, Any], *, ok: bool = True
) -> list[dict[str, Any]]:
    return [
        invocation(f"t{n}", name, json.dumps(args), time_sec=1.0 + n),
        result(f"t{n}", '{"status": "booked"}', successful=ok, time_sec=1.5 + n),
    ]


def _run(check: Any, *tools: list[dict[str, Any]]) -> list[Raised]:
    timeline = [speech("agent", "Hello", 0.5)] + [e for tool in tools for e in tool]
    trace = retell_call_to_trace(retell_call("call_invented", timeline=timeline))
    return check.run(CheckInput(trace=trace, executions=[]))


@pytest.mark.parametrize(
    ("name", "books"),
    [
        ("schedule_appointment", True),
        ("book_visit", True),
        ("reserveTable", True),
        ("get_availability_calendar_slots", False),
        ("check_appointment_slots", False),
        ("cancel_appointment", False),
        ("reschedule_appointment", False),
        ("technician_notification", False),
        ("end_call", False),
    ],
)
def test_a_booking_tool_is_known_by_its_name(name: str, books: bool) -> None:
    assert is_booking_tool(name) is books


def test_both_checks_are_rules_that_fail_the_call() -> None:
    for check in (BOOKING_DETAILS_MISSING, BOOKING_DUPLICATED):
        assert check.kind is CheckKind.RULE
        assert check.default_mode is CheckMode.FAILS
        assert check.category == "booking"


# ── Booking with missing or placeholder details ────────────────────


@pytest.mark.parametrize(
    "empty",
    [
        {"full_name": "{{full_name}}"},
        {"full_name": "{{name_missing}}"},
        {"streetAddress": "[address pending]"},
        {"postalCode": "00000"},
        {"postalCode": ""},
        {"full_name": "  "},
        {"streetAddress": "unknown"},
        {"full_name": None},
    ],
)
def test_an_empty_or_placeholder_detail_is_found(empty: dict[str, Any]) -> None:
    (found,) = _run(
        BOOKING_DETAILS_MISSING, _tool(1, "schedule_appointment", FULL | empty)
    )

    assert found.key == "schedule_appointment"
    assert found.detail == {"empty": sorted(empty)}
    assert found.event_ids == ("t1",)


def test_the_finding_names_arguments_never_their_values() -> None:
    (found,) = _run(
        BOOKING_DETAILS_MISSING,
        _tool(
            1, "schedule_appointment", FULL | {"full_name": "", "postalCode": "00000"}
        ),
    )

    assert found.detail == {"empty": ["full_name", "postalCode"]}
    assert "00000" not in json.dumps(found.detail)


def test_a_full_booking_and_other_tools_are_not_flagged() -> None:
    assert _run(BOOKING_DETAILS_MISSING, _tool(1, "schedule_appointment", FULL)) == []
    # Placeholders in arguments that are not a name, address or zip.
    assert (
        _run(
            BOOKING_DETAILS_MISSING,
            _tool(1, "schedule_appointment", FULL | {"email": "", "Model": "unknown"}),
        )
        == []
    )
    # Not a booking tool.
    assert (
        _run(BOOKING_DETAILS_MISSING, _tool(1, "lookup_customer", {"full_name": ""}))
        == []
    )


def test_each_booking_call_is_judged_on_its_own() -> None:
    found = _run(
        BOOKING_DETAILS_MISSING,
        _tool(1, "schedule_appointment", FULL | {"streetAddress": ""}),
        _tool(2, "schedule_appointment", FULL),
    )

    assert [f.event_ids for f in found] == [("t1",)]


# ── Two bookings for one slot ──────────────────────────────────────


def test_the_same_slot_booked_twice_is_found() -> None:
    (found,) = _run(
        BOOKING_DUPLICATED,
        _tool(1, "schedule_appointment", FULL | {"streetAddress": ""}),
        _tool(2, "schedule_appointment", FULL),
    )

    assert found.key == "schedule_appointment"
    assert found.event_ids == ("t1", "t2")


def test_three_bookings_for_one_slot_are_two_findings() -> None:
    found = _run(
        BOOKING_DUPLICATED,
        _tool(1, "schedule_appointment", FULL),
        _tool(2, "schedule_appointment", FULL),
        _tool(3, "schedule_appointment", FULL),
    )

    assert [f.event_ids for f in found] == [("t1", "t2"), ("t1", "t3")]


def test_bookings_at_different_times_or_that_failed_are_not_flagged() -> None:
    later = FULL | {"startTime": "2026-10-23T14:00:00-04:00"}
    assert (
        _run(
            BOOKING_DUPLICATED,
            _tool(1, "schedule_appointment", FULL),
            _tool(2, "schedule_appointment", later),
        )
        == []
    )
    assert (
        _run(
            BOOKING_DUPLICATED,
            _tool(1, "schedule_appointment", FULL, ok=False),
            _tool(2, "schedule_appointment", FULL),
        )
        == []
    )


def test_the_time_zone_is_not_taken_for_the_time() -> None:
    # Same time zone, different start times: two separate slots.
    a = FULL | {"startTime": "2026-10-23T09:00:00-04:00"}
    b = FULL | {"startTime": "2026-10-23T12:00:00-04:00"}

    assert (
        _run(
            BOOKING_DUPLICATED,
            _tool(1, "schedule_appointment", a),
            _tool(2, "schedule_appointment", b),
        )
        == []
    )
