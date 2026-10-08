"""Retell payload -> trace. Every payload here is invented."""

from datetime import UTC, datetime
from typing import Any

import pytest

from app.models.enums import (
    CallChannel,
    CallDirection,
    CallEndReason,
    Speaker,
    ToolCallStatus,
    TraceCapability,
)
from app.models.trace import MarkerEvent, ToolCallEvent, Trace, UtteranceEvent
from app.services.mappings.retell import (
    _END_REASONS,
    RetellMappingError,
    retell_call_to_trace,
)
from app.services.trace_capabilities import derive_capabilities
from app.tests.utils.retell_payloads import (
    START_MS,
    invocation,
    result,
    retell_call,
    speech,
)


def _tool_calls(trace: Trace) -> list[ToolCallEvent]:
    return [e for e in trace.events if isinstance(e, ToolCallEvent)]


def _utterances(trace: Trace) -> list[UtteranceEvent]:
    return [e for e in trace.events if isinstance(e, UtteranceEvent)]


def _markers(trace: Trace) -> list[MarkerEvent]:
    return [e for e in trace.events if isinstance(e, MarkerEvent)]


def test_plain_conversation() -> None:
    trace = retell_call_to_trace(retell_call())

    assert trace.provider == "retell"
    assert trace.external_id == "call_invented_1"
    assert trace.started_at == datetime.fromtimestamp(START_MS / 1000, tz=UTC)
    assert trace.ended_at == datetime.fromtimestamp(START_MS / 1000 + 60, tz=UTC)
    assert trace.channel == CallChannel.PHONE
    assert trace.direction == CallDirection.INBOUND
    assert trace.end_reason == CallEndReason.CALLER_HANGUP
    assert trace.end_reason_detail == "user_hangup"
    assert trace.reports_tool_calls is True
    assert trace.recording_url == "https://recordings.example.com/call_invented_1.wav"
    assert trace.inputs == {"customer_name": "Sam Example"}

    # Inbound: the caller is "from", the agent is "to".
    assert trace.parties is not None
    assert trace.parties.caller_number == "+15550100001"
    assert trace.parties.agent_number == "+15550100002"

    assert trace.components is not None
    agent = trace.components[0]
    assert (agent.kind, agent.name, agent.ref, agent.version) == (
        "agent",
        "Invented Agent",
        "agent_invented_1",
        "7",
    )

    first, second = _utterances(trace)
    assert (first.speaker, first.text) == (
        Speaker.AGENT,
        "Hello this is the invented agent",
    )
    assert (first.start_ms, first.end_ms) == (500, 2800)
    assert (second.speaker, second.text) == (Speaker.CALLER, "Hi I have a question")
    assert [e.id for e in trace.events] == ["e1", "e2"]

    assert trace.extensions is not None
    assert set(trace.extensions) == {
        "call_status",
        "duration_ms",
        "latency",
        "call_cost",
        "metadata",
        "public_log_url",
    }
    assert trace.outputs is None


def test_outbound_call_swaps_the_parties() -> None:
    trace = retell_call_to_trace(retell_call(direction="outbound"))
    assert trace.direction == CallDirection.OUTBOUND
    assert trace.parties is not None
    assert trace.parties.agent_number == "+15550100001"
    assert trace.parties.caller_number == "+15550100002"


def test_tool_call_with_successful_result() -> None:
    trace = retell_call_to_trace(
        retell_call(
            timeline=[
                speech("user", "What is the price", 1.0),
                invocation("tc_1", "get_price", '{"sku": "A-1"}', time_sec=3.0),
                result("tc_1", '{"price": 120}', successful=True, time_sec=4.5),
                speech("agent", "It is one hundred and twenty", 5.0),
            ]
        )
    )
    (call,) = _tool_calls(trace)
    assert call.id == "tc_1"
    assert call.name == "get_price"
    assert call.arguments == {"sku": "A-1"}
    assert call.status == ToolCallStatus.OK
    assert call.result == {"price": 120}
    assert (call.start_ms, call.end_ms) == (3000, 4500)
    # The result is joined into the call, not kept as a separate event.
    assert [e.type for e in trace.events] == ["utterance", "tool_call", "utterance"]

    capabilities = derive_capabilities(trace)
    assert TraceCapability.TOOL_CALLS in capabilities
    assert TraceCapability.TOOL_RESULTS in capabilities
    assert TraceCapability.TIMING in capabilities


def test_tool_call_with_failed_result() -> None:
    trace = retell_call_to_trace(
        retell_call(
            timeline=[
                invocation("tc_1", "get_price", "{}", time_sec=3.0),
                result("tc_1", "upstream timed out", successful=False, time_sec=9.0),
            ]
        )
    )
    (call,) = _tool_calls(trace)
    assert call.status == ToolCallStatus.ERROR
    # A result that is not JSON is kept as text.
    assert call.result == "upstream timed out"


def test_tool_call_with_no_result() -> None:
    trace = retell_call_to_trace(
        retell_call(
            timeline=[
                speech("agent", "Goodbye", 1.0),
                invocation("tc_end", "end_call", "", time_sec=2.0),
            ]
        )
    )
    (call,) = _tool_calls(trace)
    assert call.status == ToolCallStatus.NO_RESULT
    assert call.result is None
    assert call.arguments is None
    assert call.end_ms is None


def test_result_without_its_invocation_is_kept() -> None:
    trace = retell_call_to_trace(
        retell_call(timeline=[result("tc_lost", '{"ok": true}', time_sec=2.0)])
    )
    (call,) = _tool_calls(trace)
    assert call.name == "unknown_tool"
    assert call.status == ToolCallStatus.OK
    assert call.result == {"ok": True}


def test_arguments_that_are_not_an_object_are_kept() -> None:
    trace = retell_call_to_trace(
        retell_call(timeline=[invocation("tc_1", "lookup", '"A-1"', time_sec=1.0)])
    )
    assert _tool_calls(trace)[0].arguments == {"value": "A-1"}


def test_transfer_has_a_third_speaker() -> None:
    trace = retell_call_to_trace(
        retell_call(
            disconnection_reason="call_transfer",
            timeline=[
                speech("agent", "Let me connect you", 1.0),
                speech("transfer_target", "Sales desk speaking", 8.0),
                speech("user", "Hello", 10.0),
            ],
        )
    )
    assert [u.speaker for u in _utterances(trace)] == [
        Speaker.AGENT,
        Speaker.OTHER,
        Speaker.CALLER,
    ]
    assert trace.end_reason == CallEndReason.TRANSFER


def test_keypad_press_and_node_transition_become_markers() -> None:
    trace = retell_call_to_trace(
        retell_call(
            timeline=[
                speech("agent", "Press one for sales", 1.0),
                {"role": "dtmf", "digit": "1", "time_sec": 4.0},
                {
                    "role": "node_transition",
                    "former_node_name": "menu",
                    "new_node_name": "sales",
                    "time_sec": 4.2,
                },
            ]
        )
    )
    keypad, transition = _markers(trace)
    assert (keypad.name, keypad.detail, keypad.start_ms) == (
        "dtmf",
        {"digit": "1"},
        4000,
    )
    assert transition.name == "node_transition"
    assert transition.detail == {"former_node_name": "menu", "new_node_name": "sales"}


def test_web_call_has_no_parties() -> None:
    payload = retell_call(call_type="web_call")
    for key in ("direction", "from_number", "to_number"):
        del payload[key]
    trace = retell_call_to_trace(payload)
    assert trace.channel == CallChannel.WEB
    assert trace.direction is None
    assert trace.parties is None


def test_call_that_never_connected() -> None:
    payload = retell_call(start_ms=None, disconnection_reason="dial_no_answer")
    del payload["transcript_with_tool_calls"]
    payload["end_timestamp"] = START_MS
    trace = retell_call_to_trace(payload)

    assert trace.events == []
    assert trace.end_reason == CallEndReason.NO_ANSWER
    # With no start, the call is placed at the moment it ended.
    assert trace.started_at == trace.ended_at
    assert TraceCapability.TOOL_CALLS in derive_capabilities(trace)


def test_events_are_ordered_by_start_time() -> None:
    # Retell lists overlapping speech in the order it finished recognising it.
    trace = retell_call_to_trace(
        retell_call(
            timeline=[
                speech("agent", "Second by time", 5.0),
                speech("user", "First by time", 4.0),
                {"role": "injected", "content": "untimed note"},
                speech("agent", "Third", 9.0),
            ]
        )
    )
    assert [getattr(e, "text", None) or e.type for e in trace.events] == [
        "First by time",
        # No time of its own: it stays right after the item it followed.
        "marker",
        "Second by time",
        "Third",
    ]
    assert [e.id for e in trace.events] == ["e1", "e2", "e3", "e4"]


def test_an_item_with_no_time_stays_after_the_item_before_it() -> None:
    trace = retell_call_to_trace(
        retell_call(
            timeline=[
                speech("agent", "One", 5.0),
                {"role": "user", "content": "No timings"},
                speech("agent", "Two", 6.0),
            ]
        )
    )
    assert [u.text for u in _utterances(trace)] == ["One", "No timings", "Two"]
    assert _utterances(trace)[1].start_ms is None
    assert TraceCapability.TIMING not in derive_capabilities(trace)


def test_speech_only_payload_falls_back_to_transcript_object() -> None:
    payload = retell_call()
    payload["transcript_object"] = payload.pop("transcript_with_tool_calls")
    assert len(_utterances(retell_call_to_trace(payload))) == 2


def test_analysis_and_collected_variables_become_outputs() -> None:
    trace = retell_call_to_trace(
        retell_call(
            call_analysis={"call_summary": "Asked a question", "call_successful": True},
            collected_dynamic_variables={"callback_time": "tomorrow"},
        )
    )
    assert trace.outputs == {
        "call_summary": "Asked a question",
        "call_successful": True,
        "collected_dynamic_variables": {"callback_time": "tomorrow"},
    }
    assert TraceCapability.OUTPUTS in derive_capabilities(trace)


def test_an_over_long_recording_link_is_left_out() -> None:
    trace = retell_call_to_trace(
        retell_call(recording_url="https://recordings.example.com/" + "a" * 2100)
    )
    assert trace.recording_url is None


@pytest.mark.parametrize("reason", sorted(_END_REASONS))
def test_every_known_disconnection_reason_maps_to_a_fixed_reason(reason: str) -> None:
    trace = retell_call_to_trace(retell_call(disconnection_reason=reason))
    assert trace.end_reason is not None
    assert trace.end_reason != CallEndReason.UNKNOWN
    assert trace.end_reason_detail == reason


def test_a_reason_retell_adds_later_maps_to_unknown_and_keeps_its_text() -> None:
    trace = retell_call_to_trace(retell_call(disconnection_reason="brand_new_reason"))
    assert trace.end_reason == CallEndReason.UNKNOWN
    assert trace.end_reason_detail == "brand_new_reason"


def test_no_reason_means_no_end_reason() -> None:
    payload = retell_call()
    del payload["disconnection_reason"]
    trace = retell_call_to_trace(payload)
    assert trace.end_reason is None
    assert trace.end_reason_detail is None


@pytest.mark.parametrize(
    "payload",
    [
        {"agent_id": "agent_invented_1", "start_timestamp": START_MS},
        {"call_id": "", "start_timestamp": START_MS},
        {"call_id": "call_invented_1"},
        {"call_id": "call_invented_1", "start_timestamp": "yesterday"},
    ],
)
def test_a_payload_without_identity_or_time_is_refused(payload: dict[str, Any]) -> None:
    with pytest.raises(RetellMappingError):
        retell_call_to_trace(payload)


def test_malformed_timeline_items_are_skipped() -> None:
    trace = retell_call_to_trace(
        retell_call(timeline=["not an item", speech("agent", "Hello", 1.0)])  # type: ignore[list-item]
    )
    assert len(trace.events) == 1
