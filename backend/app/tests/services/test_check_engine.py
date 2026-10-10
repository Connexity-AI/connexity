"""The pure part of the check engine: checks and facts over an invented trace."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from app.models.check import DecisionRecord
from app.models.enums import CheckMode, DecisionKind, ToolCallStatus
from app.models.execution import Execution
from app.models.trace import ToolCallEvent, Trace, UtteranceEvent
from app.services.checks.base import (
    CheckInput,
    Fact,
    FactSource,
    Raised,
    RuleCheck,
)
from app.services.checks.engine import (
    CheckError,
    current_mode,
    is_loosening,
    mode_at,
    run_checks,
)
from app.services.checks.registry import CHECKS
from app.services.checks.rules.tool_call_failed import TOOL_CALL_FAILED

NOON = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _trace(*statuses: ToolCallStatus | None) -> Trace:
    return Trace(
        provider="invented",
        external_id="call-1",
        started_at=NOON,
        events=[
            UtteranceEvent(id="u1", speaker="caller", text="Is there a table at eight"),
            *(
                ToolCallEvent(id=f"t{index}", name="find_table", status=status)
                for index, status in enumerate(statuses, start=1)
            ),
        ],
    )


def _check(
    run: Callable[[CheckInput], list[Raised]],
    facts: tuple[str, ...] = (),
    check_type: str = "invented",
) -> RuleCheck:
    return RuleCheck(
        type=check_type,
        version=3,
        title="Invented",
        description="For tests.",
        default_mode=CheckMode.FLAGS,
        run=run,
        facts=facts,
    )


def _setting(old: CheckMode, new: CheckMode, at: datetime) -> DecisionRecord:
    return DecisionRecord(
        kind=DecisionKind.CHECK_SETTING,
        subject=TOOL_CALL_FAILED.type,
        old_value=old.value,
        new_value=new.value,
        decided_by_email="someone@example.com",
        created_at=at,
    )


# ── Tool call failed ───────────────────────────────────────────────


@pytest.mark.parametrize("status", [ToolCallStatus.ERROR, ToolCallStatus.TIMEOUT])
def test_a_failed_tool_call_raises_one_finding_on_that_event(
    status: ToolCallStatus,
) -> None:
    run = run_checks(
        trace=_trace(ToolCallStatus.OK, status), executions=[], checks=CHECKS
    )

    assert run.broken == {}
    ((check, raised),) = run.found
    assert check is TOOL_CALL_FAILED
    assert raised.event_ids == ("t2",)
    assert raised.key == "find_table"
    assert raised.detail == {"status": status.value}


@pytest.mark.parametrize("status", [ToolCallStatus.OK, ToolCallStatus.NO_RESULT, None])
def test_a_tool_call_that_did_not_fail_raises_nothing(
    status: ToolCallStatus | None,
) -> None:
    run = run_checks(trace=_trace(status), executions=[], checks=CHECKS)
    assert (run.found, run.broken) == ([], {})


def test_each_failed_tool_call_is_its_own_finding() -> None:
    run = run_checks(
        trace=_trace(ToolCallStatus.ERROR, ToolCallStatus.ERROR),
        executions=[],
        checks=CHECKS,
    )
    assert [raised.event_ids for _, raised in run.found] == [("t1",), ("t2",)]


def test_built_in_check_types_are_unique() -> None:
    types = [check.type for check in CHECKS]
    assert len(types) == len(set(types))


# ── Facts ──────────────────────────────────────────────────────────


def test_a_check_receives_the_facts_it_asked_for_and_only_those() -> None:
    derived: list[str] = []

    def tool_calls(trace: Trace, _executions: list[Execution]) -> list[Fact]:
        derived.append("tool_calls")
        return [
            Fact(event_ids=(event.id,), value=event.name)
            for event in trace.events
            if isinstance(event, ToolCallEvent)
        ]

    def never(_trace: Trace, _executions: list[Execution]) -> list[Fact]:
        derived.append("never")
        return []

    seen: list[dict[str, list[Fact]]] = []

    def run(check_input: CheckInput) -> list[Raised]:
        seen.append(dict(check_input.facts))
        return [
            Raised(event_ids=fact.event_ids) for fact in check_input.facts["tool_calls"]
        ]

    result = run_checks(
        trace=_trace(ToolCallStatus.OK),
        executions=[],
        checks=[
            _check(run, facts=("tool_calls",)),
            _check(run, facts=("tool_calls",), check_type="invented_2"),
        ],
        fact_sources=[
            FactSource(name="tool_calls", version=1, derive=tool_calls),
            FactSource(name="never", version=1, derive=never),
        ],
    )

    assert result.broken == {}
    assert [raised.event_ids for _, raised in result.found] == [("t1",), ("t1",)]
    assert seen[0] == {"tool_calls": [Fact(event_ids=("t1",), value="find_table")]}
    # Derived once for the call, however many checks use it; an unused one never.
    assert derived == ["tool_calls"]


def test_a_check_that_needs_a_fact_nothing_derives_is_broken() -> None:
    run = run_checks(
        trace=_trace(),
        executions=[],
        checks=[_check(lambda _input: [], facts=("missing",))],
    )

    assert run.found == []
    assert isinstance(run.broken["invented"], CheckError)
    assert "needs fact 'missing'" in str(run.broken["invented"])


# ── What a check may not do ────────────────────────────────────────


@pytest.mark.parametrize(
    ("raised", "message"),
    [
        ([Raised(event_ids=())], "points at no event"),
        ([Raised(event_ids=("nope",))], "does not have"),
        ([Raised(event_ids=("u1",)), Raised(event_ids=("u1",))], "two findings"),
    ],
)
def test_a_finding_must_point_at_real_events_once(
    raised: list[Raised], message: str
) -> None:
    run = run_checks(
        trace=_trace(), executions=[], checks=[_check(lambda _input: raised)]
    )

    assert run.found == []
    assert message in str(run.broken["invented"])


def test_a_check_that_breaks_does_not_stop_the_others() -> None:
    def broken(_input: CheckInput) -> list[Raised]:
        raise RuntimeError("anything at all")

    run = run_checks(
        trace=_trace(ToolCallStatus.ERROR),
        executions=[],
        checks=[_check(broken), *CHECKS],
    )

    assert list(run.broken) == ["invented"]
    assert [check.type for check, _ in run.found] == [TOOL_CALL_FAILED.type]


# ── Settings over time ─────────────────────────────────────────────


def test_a_check_with_no_decisions_has_its_default() -> None:
    assert mode_at(TOOL_CALL_FAILED, [], NOON) is CheckMode.FAILS


def test_a_decision_applies_from_the_moment_it_was_made() -> None:
    records = [
        _setting(CheckMode.FAILS, CheckMode.FLAGS, NOON),
        _setting(CheckMode.FLAGS, CheckMode.OFF, NOON + timedelta(hours=1)),
    ]
    minute = timedelta(minutes=1)

    assert mode_at(TOOL_CALL_FAILED, records, NOON - minute) is CheckMode.FAILS
    assert mode_at(TOOL_CALL_FAILED, records, NOON) is CheckMode.FLAGS
    assert mode_at(TOOL_CALL_FAILED, records, NOON + minute) is CheckMode.FLAGS
    assert mode_at(TOOL_CALL_FAILED, records, NOON + 2 * minute * 60) is CheckMode.OFF


def test_the_current_setting_is_the_latest_decision_whatever_the_clock_says() -> None:
    ahead = datetime.now(UTC) + timedelta(minutes=5)

    assert current_mode(TOOL_CALL_FAILED, []) is CheckMode.FAILS
    assert (
        current_mode(
            TOOL_CALL_FAILED, [_setting(CheckMode.FAILS, CheckMode.FLAGS, ahead)]
        )
        is CheckMode.FLAGS
    )


@pytest.mark.parametrize(
    ("old", "new", "loosens"),
    [
        (CheckMode.FAILS, CheckMode.FLAGS, True),
        (CheckMode.FAILS, CheckMode.OFF, True),
        (CheckMode.FLAGS, CheckMode.OFF, True),
        (CheckMode.OFF, CheckMode.FLAGS, False),
        (CheckMode.FLAGS, CheckMode.FAILS, False),
        (CheckMode.OFF, CheckMode.FAILS, False),
    ],
)
def test_loosening_is_any_step_towards_off(
    old: CheckMode, new: CheckMode, loosens: bool
) -> None:
    assert is_loosening(old, new) is loosens
