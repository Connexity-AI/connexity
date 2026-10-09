"""n8n execution -> an execution with steps, and what its trigger says about the caller.

Built from the shape of real executions. An n8n execution keeps each node's output; a
node's input is the output of the nodes before it, so a step records which steps fed it
instead of a second copy of the data.
"""

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, JsonValue

from app.models.enums import ExecutionMatch, ExecutionStatus
from app.models.execution import Execution, ExecutionStep

PROVIDER = "n8n"

# Stored node data per execution. Past either limit a step is kept without its output.
MAX_STEPS = 200
MAX_OUTPUT_BYTES = 2_000_000

_TRIGGER_KIND = "webhook"

_STATUSES: dict[str, ExecutionStatus] = {
    "success": ExecutionStatus.OK,
    "error": ExecutionStatus.ERROR,
    "crashed": ExecutionStatus.ERROR,
    "running": ExecutionStatus.RUNNING,
    "waiting": ExecutionStatus.RUNNING,
    "new": ExecutionStatus.RUNNING,
    "canceled": ExecutionStatus.CANCELED,
}


class N8nMappingError(ValueError):
    """The payload is not an n8n execution that can be read."""


class ToolRequest(BaseModel):
    """What a voice provider sent to start the execution, read from its trigger."""

    # The provider's id for the call. ``None`` when the tool sends arguments only.
    call_id: str | None = None
    tool_name: str | None = None
    arguments: dict[str, JsonValue] | None = None


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if isinstance(value, int | float) and not isinstance(value, bool):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    return None


def _kind(node_type: Any) -> str | None:
    """``n8n-nodes-base.httpRequest`` -> ``httpRequest``."""
    if not isinstance(node_type, str) or not node_type:
        return None
    return node_type.rsplit(".", 1)[-1][:255]


def _node_kinds(payload: dict[str, Any]) -> dict[str, str | None]:
    workflow = payload.get("workflowData")
    nodes = workflow.get("nodes") if isinstance(workflow, dict) else None
    return {
        str(node["name"]): _kind(node.get("type"))
        for node in (nodes if isinstance(nodes, list) else [])
        if isinstance(node, dict) and node.get("name") is not None
    }


def _run_data(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    data = payload.get("data")
    result = data.get("resultData") if isinstance(data, dict) else None
    run_data = result.get("runData") if isinstance(result, dict) else None
    if not isinstance(run_data, dict):
        return {}
    return {
        str(name): [run for run in runs if isinstance(run, dict)]
        for name, runs in run_data.items()
        if isinstance(runs, list)
    }


def _scrub(value: Any) -> Any:
    """Remove what a trigger received that must not be stored, wherever it reappears.

    Nodes often pass their input through, so the trigger's item shows up again in later
    steps. Its request headers carry the provider's signature, and its ``call`` is a
    copy of the whole call, transcript included, which the trace already holds.
    """
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if not isinstance(value, dict):
        return value
    cleaned = {key: _scrub(item) for key, item in value.items()}
    if "headers" in cleaned and "webhookUrl" in cleaned:
        del cleaned["headers"]
    call = value.get("call")
    if isinstance(call, dict) and "call_id" in call:
        cleaned["call"] = {"call_id": call["call_id"]}
    return cleaned


def _items(branch: Any) -> list[JsonValue]:
    return [
        _scrub(item.get("json"))
        for item in (branch if isinstance(branch, list) else [])
        if isinstance(item, dict)
    ]


def _raw_items(branch: Any) -> list[Any]:
    return [
        item.get("json")
        for item in (branch if isinstance(branch, list) else [])
        if isinstance(item, dict)
    ]


def _output(run: dict[str, Any]) -> JsonValue:
    """A node run's output: its items, or its items per output when it has several."""
    data = run.get("data")
    if not isinstance(data, dict) or not data:
        return None
    outputs: dict[str, JsonValue] = {}
    for connection, branches in data.items():
        if not isinstance(branches, list):
            continue
        for index, branch in enumerate(branches):
            if branch is None:
                continue
            key = connection if len(branches) == 1 else f"{connection}[{index}]"
            outputs[str(key)] = _items(branch)
    if list(outputs) == ["main"]:
        return outputs["main"]
    return outputs or None


def _error(run: dict[str, Any]) -> JsonValue:
    error = run.get("error")
    if error is None:
        return None
    if not isinstance(error, dict):
        return str(error)
    kept = {
        key: error[key]
        for key in ("message", "description", "name", "httpCode", "type")
        if error.get(key) is not None
    }
    return kept or "The node failed"


def _input_from(run: dict[str, Any]) -> list[str]:
    source = run.get("source")
    names: list[str] = []
    for item in source if isinstance(source, list) else []:
        if isinstance(item, dict) and item.get("previousNode") is not None:
            name = str(item["previousNode"])
            if name not in names:
                names.append(name)
    return names


def _trigger_body(payload: dict[str, Any]) -> Any:
    kinds = _node_kinds(payload)
    for name, runs in _run_data(payload).items():
        if kinds.get(name) != _TRIGGER_KIND or not runs:
            continue
        data = runs[0].get("data")
        branches = data.get("main") if isinstance(data, dict) else None
        items = (
            _raw_items(branches[0]) if isinstance(branches, list) and branches else []
        )
        if items and isinstance(items[0], dict):
            return items[0].get("body")
    return None


def n8n_tool_request(payload: dict[str, Any]) -> ToolRequest | None:
    """What the trigger of a webhook-started execution received, if it can be read.

    A voice provider sends either the tool's name, its arguments and the call, or the
    arguments alone as the whole body.
    """
    body = _trigger_body(payload)
    if not isinstance(body, dict):
        return None
    call = body.get("call")
    if isinstance(call, dict) and "args" in body:
        call_id = call.get("call_id")
        arguments = body.get("args")
        name = body.get("name")
        if arguments is not None and not isinstance(arguments, dict):
            # The trace keeps arguments that are not an object the same way.
            arguments = {"value": arguments}
        return ToolRequest(
            call_id=call_id if isinstance(call_id, str) and call_id else None,
            tool_name=name if isinstance(name, str) and name else None,
            arguments=arguments or None,
        )
    return ToolRequest(arguments=body)


def _trigger_output(request: ToolRequest | None) -> JsonValue:
    # The trigger also received request headers (which carry a signature) and, from
    # Retell, a copy of the whole call. Neither is kept: the trace already has the call.
    if request is None:
        return None
    kept: dict[str, JsonValue] = {"arguments": request.arguments}
    if request.tool_name is not None:
        kept["name"] = request.tool_name
    return kept


def n8n_execution_to_execution(
    payload: dict[str, Any], *, event_id: str, match: ExecutionMatch
) -> Execution:
    """Convert one n8n execution (fetched with its data) for the tool call ``event_id``.

    Raises:
        N8nMappingError: The payload has no execution id.
    """
    execution_id = payload.get("id")
    if execution_id is None:
        msg = "n8n execution has no id"
        raise N8nMappingError(msg)

    kinds = _node_kinds(payload)
    request = n8n_tool_request(payload)

    runs: list[tuple[int, int, str, dict[str, Any]]] = []
    for name, node_runs in _run_data(payload).items():
        for run in node_runs:
            index = run.get("executionIndex")
            start = run.get("startTime")
            runs.append(
                (
                    index if isinstance(index, int) else len(runs),
                    start if isinstance(start, int) else 0,
                    name,
                    run,
                )
            )
    runs.sort(key=lambda entry: (entry[0], entry[1]))

    steps: list[ExecutionStep] = []
    stored_bytes = 0
    for position, (_, _, name, run) in enumerate(runs):
        kind = kinds.get(name)
        output = _trigger_output(request) if kind == _TRIGGER_KIND else _output(run)
        dropped = False
        if output is not None:
            size = len(json.dumps(output, default=str))
            if position >= MAX_STEPS or stored_bytes + size > MAX_OUTPUT_BYTES:
                output, dropped = None, True
            else:
                stored_bytes += size
        error = _error(run)
        duration = run.get("executionTime")
        steps.append(
            ExecutionStep(
                name=name[:255],
                kind=kind,
                status=ExecutionStatus.ERROR
                if error is not None or run.get("executionStatus") == "error"
                else _STATUSES.get(str(run.get("executionStatus")), ExecutionStatus.OK),
                started_at=_timestamp(run.get("startTime")),
                duration_ms=duration if isinstance(duration, int) else None,
                input_from=_input_from(run),
                output=output,
                error=error,
                data_dropped=dropped,
            )
        )

    workflow = payload.get("workflowData")
    workflow_name = workflow.get("name") if isinstance(workflow, dict) else None
    workflow_id = payload.get("workflowId")
    version = payload.get("workflowVersionId") or (
        workflow.get("versionId") if isinstance(workflow, dict) else None
    )
    return Execution(
        event_id=event_id,
        provider=PROVIDER,
        external_id=str(execution_id),
        workflow_id=str(workflow_id) if workflow_id is not None else None,
        workflow_name=str(workflow_name)[:255] if workflow_name else None,
        workflow_version=str(version)[:255] if version else None,
        status=_STATUSES.get(str(payload.get("status")), ExecutionStatus.UNKNOWN),
        started_at=_timestamp(payload.get("startedAt")),
        ended_at=_timestamp(payload.get("stoppedAt")),
        match=match,
        steps=steps,
    )
