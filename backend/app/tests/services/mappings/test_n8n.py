"""n8n execution -> execution with steps. Every payload here is invented."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from app.models.enums import ExecutionMatch, ExecutionStatus
from app.services.mappings import n8n as mapping
from app.services.mappings.n8n import (
    N8nMappingError,
    n8n_execution_to_execution,
    n8n_tool_request,
)
from app.tests.utils.n8n_payloads import n8n_execution, node_run

AT = datetime(2026, 6, 1, 12, 0, 5, tzinfo=UTC)


def _convert(payload: dict[str, Any], match: ExecutionMatch = ExecutionMatch.EXACT):
    return n8n_execution_to_execution(payload, event_id="tc_1", match=match)


def test_a_successful_execution() -> None:
    execution = _convert(n8n_execution("9001", started_at=AT))

    assert execution.event_id == "tc_1"
    assert (execution.provider, execution.external_id) == ("n8n", "9001")
    assert execution.workflow_id == "wf_invented_1"
    assert execution.workflow_name == "Invented price lookup"
    assert execution.workflow_version == "version_invented_7"
    assert execution.status == ExecutionStatus.OK
    assert execution.started_at == AT
    assert execution.match == ExecutionMatch.EXACT

    assert [(s.name, s.kind) for s in execution.steps] == [
        ("Webhook", "webhook"),
        ("Look up", "httpRequest"),
        ("Respond", "respondToWebhook"),
    ]
    look_up = execution.steps[1]
    assert look_up.status == ExecutionStatus.OK
    assert look_up.output == [{"price": 120}]
    assert look_up.input_from == ["Webhook"]
    assert look_up.duration_ms == 20
    assert look_up.started_at is not None
    assert execution.steps[2].input_from == ["Look up"]


def test_the_trigger_keeps_only_the_tool_name_and_arguments() -> None:
    execution = _convert(n8n_execution("9001", started_at=AT, args={"sku": "B-2"}))
    trigger = execution.steps[0]
    assert trigger.output == {"name": "get_price", "arguments": {"sku": "B-2"}}
    stored = json.dumps(execution.model_dump(mode="json"))
    # Neither the request headers nor the copy of the call are kept.
    assert "x-retell-signature" not in stored
    assert "transcript" not in stored


def test_a_failed_node() -> None:
    execution = _convert(n8n_execution("9002", started_at=AT, failing=True))
    assert execution.status == ExecutionStatus.ERROR
    failed = execution.steps[-1]
    assert failed.name == "Look up"
    assert failed.status == ExecutionStatus.ERROR
    assert failed.output is None
    assert failed.error == {
        "message": "Request failed with status code 500",
        "description": "invented upstream error",
        "httpCode": "500",
    }


def test_steps_are_ordered_by_when_they_ran_and_a_node_can_run_twice() -> None:
    payload = n8n_execution("9003", started_at=AT)
    start = int(AT.timestamp() * 1000)
    payload["data"]["resultData"]["runData"] = {
        "Later": [node_run([{"n": 3}], index=2, start_ms=start + 30)],
        "Loop": [
            node_run([{"n": 1}], index=0, start_ms=start),
            node_run([{"n": 2}], index=1, start_ms=start + 10),
        ],
    }
    execution = _convert(payload)
    assert [(s.name, s.output) for s in execution.steps] == [
        ("Loop", [{"n": 1}]),
        ("Loop", [{"n": 2}]),
        ("Later", [{"n": 3}]),
    ]


def test_a_node_with_several_outputs_keeps_each() -> None:
    payload = n8n_execution("9004", started_at=AT)
    run = node_run([{"x": 1}], index=1, start_ms=0)
    run["data"] = {
        "main": [[{"json": {"yes": True}}], [{"json": {"no": True}}], None],
        "ai_tool": [[{"json": {"used": "calculator"}}]],
    }
    payload["data"]["resultData"]["runData"] = {"If": [run]}
    assert _convert(payload).steps[0].output == {
        "main[0]": [{"yes": True}],
        "main[1]": [{"no": True}],
        "ai_tool": [{"used": "calculator"}],
    }


def test_output_past_the_size_limit_is_dropped_and_marked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mapping, "MAX_OUTPUT_BYTES", 150)
    execution = _convert(
        n8n_execution("9005", started_at=AT, response={"blob": "x" * 500})
    )
    respond = execution.steps[-1]
    assert (respond.output, respond.data_dropped) == (None, True)
    assert execution.steps[1].data_dropped is False


def test_steps_past_the_step_limit_keep_no_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mapping, "MAX_STEPS", 2)
    execution = _convert(n8n_execution("9006", started_at=AT))
    assert [s.data_dropped for s in execution.steps] == [False, False, True]
    assert len(execution.steps) == 3


def test_tool_request_with_the_call() -> None:
    request = n8n_tool_request(
        n8n_execution("1", started_at=AT, call_id="call_x", args={"a": 1})
    )
    assert request is not None
    assert (request.call_id, request.tool_name, request.arguments) == (
        "call_x",
        "get_price",
        {"a": 1},
    )


def test_tool_request_with_arguments_only() -> None:
    request = n8n_tool_request(
        n8n_execution("1", started_at=AT, call_id=None, args={"a": 1})
    )
    assert request is not None
    assert (request.call_id, request.tool_name, request.arguments) == (
        None,
        None,
        {"a": 1},
    )


@pytest.mark.parametrize("body", [None, "plain text", ["a", "list"], 5])
def test_a_trigger_that_is_not_a_tool_request(body: Any) -> None:
    assert n8n_tool_request(n8n_execution("1", started_at=AT, body=body)) is None


def test_an_execution_with_no_saved_data_has_no_steps() -> None:
    payload = n8n_execution("9007", started_at=AT)
    payload["data"] = None
    execution = _convert(payload)
    assert execution.steps == []
    assert n8n_tool_request(payload) is None


def test_a_payload_without_an_id_is_refused() -> None:
    with pytest.raises(N8nMappingError):
        _convert({"status": "success"})


def test_an_unknown_status_and_missing_times() -> None:
    execution = _convert({"id": 7, "status": "brand_new", "startedAt": "not a date"})
    assert execution.external_id == "7"
    assert execution.status == ExecutionStatus.UNKNOWN
    assert execution.started_at is None


def test_trigger_data_passed_through_by_a_later_node_is_not_kept() -> None:
    payload = n8n_execution("9008", started_at=AT)
    run_data = payload["data"]["resultData"]["runData"]
    trigger_item = run_data["Webhook"][0]["data"]["main"][0][0]["json"]
    # An If node hands its input on unchanged; a Code node nests it.
    run_data["Look up"] = [node_run([trigger_item], index=1, start_ms=5)]
    run_data["Respond"] = [
        node_run([{"wrapped": {"request": trigger_item}}], index=2, start_ms=9)
    ]
    execution = _convert(payload)
    stored = json.dumps(execution.model_dump(mode="json"))
    assert "x-retell-signature" not in stored
    assert "transcript" not in stored
    passed_on = execution.steps[1].output
    assert isinstance(passed_on, list)
    assert passed_on[0]["body"]["call"] == {"call_id": "call_invented_1"}
    assert passed_on[0]["body"]["args"] == {"sku": "A-1"}


def test_arguments_that_are_not_an_object_are_kept_like_the_trace_keeps_them() -> None:
    payload = n8n_execution("1", started_at=AT)
    body = payload["data"]["resultData"]["runData"]["Webhook"][0]["data"]["main"][0][0][
        "json"
    ]["body"]
    body["args"] = "A-1"
    request = n8n_tool_request(payload)
    assert request is not None and request.arguments == {"value": "A-1"}
    body["args"] = {}
    request = n8n_tool_request(payload)
    assert request is not None and request.arguments is None
