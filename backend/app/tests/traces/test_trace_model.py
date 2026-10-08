"""The trace wire format: what is accepted and what is rejected."""

import pytest
from pydantic import ValidationError

from app.models.enums import CallEventType, TraceSource
from app.models.trace import Trace
from app.tests.traces.examples import EXAMPLE_NAMES, load_example, load_example_json


def _minimal(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "provider": "retell",
        "external_id": "call-1",
        "started_at": "2026-10-01T10:00:00Z",
        "events": [],
    }
    base.update(overrides)
    return base


def test_there_are_three_published_examples() -> None:
    assert len(EXAMPLE_NAMES) == 3


@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_published_examples_are_valid(name: str) -> None:
    trace = load_example(name)
    assert trace.schema_version == 1
    assert trace.events


@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_published_examples_survive_json_round_trip(name: str) -> None:
    trace = load_example(name)
    assert Trace.model_validate_json(trace.model_dump_json()) == trace


def test_minimal_trace_needs_only_identity_and_events() -> None:
    trace = Trace.model_validate(_minimal())
    assert trace.source == TraceSource.PRODUCTION
    assert trace.inputs is None
    assert trace.components is None


def test_provider_is_free_text_not_a_fixed_list() -> None:
    trace = Trace.model_validate(_minimal(provider="my-own-stack_v2"))
    assert trace.provider == "my-own-stack_v2"


@pytest.mark.parametrize("provider", ["Retell", "has space", ""])
def test_provider_must_be_lower_case_without_spaces(provider: str) -> None:
    with pytest.raises(ValidationError):
        Trace.model_validate(_minimal(provider=provider))


def test_started_at_must_carry_a_time_zone() -> None:
    with pytest.raises(ValidationError):
        Trace.model_validate(_minimal(started_at="2026-10-01T10:00:00"))


def test_unknown_event_type_is_rejected() -> None:
    events = [{"id": "e1", "type": "thought", "text": "hmm"}]
    with pytest.raises(ValidationError):
        Trace.model_validate(_minimal(events=events))


def test_duplicate_event_ids_are_rejected() -> None:
    events = [
        {"id": "e1", "type": "utterance", "speaker": "agent", "text": "a"},
        {"id": "e1", "type": "utterance", "speaker": "caller", "text": "b"},
    ]
    with pytest.raises(ValidationError, match="used more than once"):
        Trace.model_validate(_minimal(events=events))


def test_unknown_tool_call_status_is_rejected() -> None:
    events = [{"id": "e1", "type": "tool_call", "name": "t", "status": "maybe"}]
    with pytest.raises(ValidationError):
        Trace.model_validate(_minimal(events=events))


def test_event_cannot_end_before_it_starts() -> None:
    events = [
        {
            "id": "e1",
            "type": "utterance",
            "speaker": "agent",
            "text": "a",
            "start_ms": 500,
            "end_ms": 100,
        }
    ]
    with pytest.raises(ValidationError, match="ends before it starts"):
        Trace.model_validate(_minimal(events=events))


def test_event_cannot_have_an_end_without_a_start() -> None:
    events = [{"id": "e1", "type": "tool_call", "name": "t", "end_ms": 100}]
    with pytest.raises(ValidationError, match="no start_ms"):
        Trace.model_validate(_minimal(events=events))


def test_call_cannot_end_before_it_starts() -> None:
    with pytest.raises(ValidationError, match="before started_at"):
        Trace.model_validate(_minimal(ended_at="2026-10-01T09:00:00Z"))


def test_unknown_top_level_field_is_rejected() -> None:
    # A mapping's typo must be an error, not silently dropped data.
    with pytest.raises(ValidationError):
        Trace.model_validate(_minimal(recordng_url="https://example.com/a.wav"))


def test_unknown_speaker_is_rejected() -> None:
    events = [{"id": "e1", "type": "utterance", "speaker": "bot", "text": "a"}]
    with pytest.raises(ValidationError):
        Trace.model_validate(_minimal(events=events))


def test_tool_result_may_be_any_json_value() -> None:
    events = [
        {"id": "a", "type": "tool_call", "name": "t", "status": "ok", "result": "raw"},
        {"id": "b", "type": "tool_call", "name": "t", "status": "ok", "result": [1, 2]},
        {"id": "c", "type": "tool_call", "name": "t", "status": "ok", "result": 7},
    ]
    trace = Trace.model_validate(_minimal(events=events))
    assert [event.type for event in trace.events] == [CallEventType.TOOL_CALL] * 3


def test_empty_components_and_parties_mean_absent() -> None:
    trace = Trace.model_validate(_minimal(components=[], parties={}))
    assert trace.components is None
    assert trace.parties is None


def test_examples_contain_no_fields_outside_the_schema() -> None:
    # Guards the examples against drifting into something the doc does not describe.
    for name in EXAMPLE_NAMES:
        raw = load_example_json(name)
        assert set(raw) <= set(Trace.model_fields), name
