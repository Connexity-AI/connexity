"""Capabilities are derived from what a trace contains."""

from app.models.enums import TraceCapability as Cap
from app.models.trace import Trace
from app.services.trace_capabilities import derive_capabilities
from app.tests.traces.examples import load_example


def _trace(**overrides: object) -> Trace:
    base: dict[str, object] = {
        "provider": "retell",
        "external_id": "call-1",
        "started_at": "2026-10-01T10:00:00Z",
        "events": [],
    }
    base.update(overrides)
    return Trace.model_validate(base)


def test_full_example_has_every_capability() -> None:
    assert set(derive_capabilities(load_example("hosted-platform-full"))) == set(Cap)


def test_partial_example_lacks_results_versions_and_recording() -> None:
    capabilities = derive_capabilities(load_example("hosted-platform-partial"))
    assert capabilities == [Cap.TOOL_CALLS, Cap.TIMING, Cap.INPUTS, Cap.OUTPUTS]


def test_text_only_example_has_no_optional_capability() -> None:
    assert derive_capabilities(load_example("self-hosted-text-only")) == []


def test_no_tool_events_is_not_proof_the_agent_called_nothing() -> None:
    utterance = {"id": "e1", "type": "utterance", "speaker": "agent", "text": "hi"}
    assert Cap.TOOL_CALLS not in derive_capabilities(_trace(events=[utterance]))


def test_mapping_can_declare_that_it_reports_tool_calls() -> None:
    utterance = {"id": "e1", "type": "utterance", "speaker": "agent", "text": "hi"}
    capabilities = derive_capabilities(
        _trace(events=[utterance], reports_tool_calls=True)
    )
    # With no tool calls at all, every one of them trivially has a result.
    assert Cap.TOOL_CALLS in capabilities
    assert Cap.TOOL_RESULTS in capabilities


def test_one_tool_call_without_status_removes_tool_results() -> None:
    events = [
        {"id": "a", "type": "tool_call", "name": "t", "status": "ok"},
        {"id": "b", "type": "tool_call", "name": "t"},
    ]
    capabilities = derive_capabilities(_trace(events=events))
    assert Cap.TOOL_CALLS in capabilities
    assert Cap.TOOL_RESULTS not in capabilities


def test_timing_needs_a_start_on_every_event() -> None:
    events = [
        {
            "id": "a",
            "type": "utterance",
            "speaker": "agent",
            "text": "x",
            "start_ms": 1,
        },
        {"id": "b", "type": "utterance", "speaker": "caller", "text": "y"},
    ]
    assert Cap.TIMING not in derive_capabilities(_trace(events=events))


def test_empty_trace_has_no_timing() -> None:
    assert Cap.TIMING not in derive_capabilities(_trace())


def test_empty_inputs_still_count_as_supplied() -> None:
    assert Cap.INPUTS in derive_capabilities(_trace(inputs={}))
    assert Cap.INPUTS not in derive_capabilities(_trace())


def test_components_need_a_version_or_fingerprint() -> None:
    unversioned = [{"kind": "agent", "name": "A", "ref": "a1"}]
    fingerprinted = [{"kind": "prompt", "name": "P", "fingerprint": "sha256:ab"}]
    assert Cap.COMPONENTS not in derive_capabilities(_trace(components=unversioned))
    assert Cap.COMPONENTS in derive_capabilities(_trace(components=fingerprinted))
