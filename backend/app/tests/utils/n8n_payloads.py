"""Invented n8n API payloads, built from the shape of n8n's execution object.

Nothing here comes from a real instance.
"""

from datetime import UTC, datetime, timedelta
from typing import Any


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def node_run(
    output: list[dict[str, Any]] | None,
    *,
    index: int,
    start_ms: int,
    duration_ms: int = 20,
    previous: str | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run: dict[str, Any] = {
        "startTime": start_ms,
        "executionTime": duration_ms,
        "executionIndex": index,
        "executionStatus": "error" if error else "success",
        "source": [{"previousNode": previous}] if previous else [],
        "hints": [],
    }
    if output is not None:
        run["data"] = {
            "main": [[{"json": item, "pairedItem": {"item": 0}} for item in output]]
        }
    if error:
        run["error"] = error
    return run


def tool_request_body(
    call_id: str | None, name: str, args: dict[str, Any]
) -> dict[str, Any]:
    """What Retell posts to a tool's webhook. ``call_id=None`` means arguments only."""
    if call_id is None:
        return dict(args)
    return {
        "name": name,
        "args": args,
        "call": {
            "call_id": call_id,
            "agent_id": "agent_invented_1",
            "transcript": "Agent: invented\nUser: invented",
        },
    }


def n8n_execution(
    execution_id: str,
    *,
    started_at: datetime,
    call_id: str | None = "call_invented_1",
    tool_name: str = "get_price",
    args: dict[str, Any] | None = None,
    response: dict[str, Any] | None = None,
    workflow_id: str = "wf_invented_1",
    failing: bool = False,
    body: Any = "tool",
) -> dict[str, Any]:
    """A webhook-started execution: Webhook -> Look up -> Respond."""
    start_ms = int(started_at.timestamp() * 1000)
    trigger_body = (
        tool_request_body(call_id, tool_name, args or {"sku": "A-1"})
        if body == "tool"
        else body
    )
    run_data: dict[str, Any] = {
        "Webhook": [
            node_run(
                [
                    {
                        "headers": {"x-retell-signature": "v=1,d=invented"},
                        "params": {},
                        "query": {},
                        "body": trigger_body,
                        "webhookUrl": "https://n8n.example.com/webhook/invented",
                        "executionMode": "production",
                    }
                ],
                index=0,
                start_ms=start_ms,
                duration_ms=1,
            )
        ],
    }
    if failing:
        run_data["Look up"] = [
            node_run(
                None,
                index=1,
                start_ms=start_ms + 5,
                previous="Webhook",
                error={
                    "message": "Request failed with status code 500",
                    "description": "invented upstream error",
                    "httpCode": "500",
                    "stack": "Error: ... (never stored)",
                },
            )
        ]
    else:
        run_data["Look up"] = [
            node_run(
                [{"price": 120}], index=1, start_ms=start_ms + 5, previous="Webhook"
            )
        ]
        run_data["Respond"] = [
            node_run(
                [response or {"price": 120}],
                index=2,
                start_ms=start_ms + 40,
                previous="Look up",
            )
        ]
    return {
        "id": execution_id,
        "finished": not failing,
        "mode": "webhook",
        "status": "error" if failing else "success",
        "startedAt": iso(started_at),
        "stoppedAt": iso(started_at + timedelta(milliseconds=60)),
        "workflowId": workflow_id,
        "workflowVersionId": "version_invented_7",
        "workflowData": {
            "id": workflow_id,
            "name": "Invented price lookup",
            "nodes": [
                {"name": "Webhook", "type": "n8n-nodes-base.webhook"},
                {"name": "Look up", "type": "n8n-nodes-base.httpRequest"},
                {"name": "Respond", "type": "n8n-nodes-base.respondToWebhook"},
            ],
        },
        "data": {
            "resultData": {
                "runData": run_data,
                "lastNodeExecuted": "Look up" if failing else "Respond",
            }
        },
    }


def execution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """The same execution as the list endpoint returns it: no node data."""
    return {
        key: payload[key]
        for key in (
            "id",
            "finished",
            "mode",
            "status",
            "startedAt",
            "stoppedAt",
            "workflowId",
        )
    }
