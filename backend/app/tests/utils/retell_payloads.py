"""Invented Retell call payloads, built from Retell's documented call object.

Nothing here comes from a real call.
"""

from typing import Any

START_MS = 1_750_000_000_000


def _words(text: str, start: float) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    cursor = start
    for word in text.split():
        words.append({"word": word, "start": cursor, "end": cursor + 0.3})
        cursor += 0.4
    return words


def speech(role: str, text: str, start: float) -> dict[str, Any]:
    return {"role": role, "content": text, "words": _words(text, start)}


def invocation(
    call_id: str, name: str, arguments: str, time_sec: float | None = None
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "role": "tool_call_invocation",
        "tool_call_id": call_id,
        "name": name,
        "arguments": arguments,
    }
    if time_sec is not None:
        item["time_sec"] = time_sec
    return item


def result(
    call_id: str,
    content: str,
    *,
    successful: bool | None = None,
    time_sec: float | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "role": "tool_call_result",
        "tool_call_id": call_id,
        "content": content,
    }
    if successful is not None:
        item["successful"] = successful
    if time_sec is not None:
        item["time_sec"] = time_sec
    return item


def retell_call(
    call_id: str = "call_invented_1",
    *,
    agent_id: str = "agent_invented_1",
    timeline: list[dict[str, Any]] | None = None,
    start_ms: int | None = START_MS,
    duration_ms: int = 60_000,
    **overrides: Any,
) -> dict[str, Any]:
    """A finished inbound phone call. ``overrides`` replace or add top-level fields."""
    payload: dict[str, Any] = {
        "call_id": call_id,
        "call_type": "phone_call",
        "agent_id": agent_id,
        "agent_name": "Invented Agent",
        "agent_version": 7,
        "call_status": "ended",
        "direction": "inbound",
        "from_number": "+15550100001",
        "to_number": "+15550100002",
        "disconnection_reason": "user_hangup",
        "recording_url": "https://recordings.example.com/call_invented_1.wav",
        "public_log_url": "https://logs.example.com/call_invented_1.log",
        "retell_llm_dynamic_variables": {"customer_name": "Sam Example"},
        "latency": {"e2e": {"p50": 800, "p90": 1200}},
        "call_cost": {"combined_cost": 12.5},
        "metadata": {"campaign": "invented"},
        "transcript_with_tool_calls": timeline
        if timeline is not None
        else [
            speech("agent", "Hello this is the invented agent", 0.5),
            speech("user", "Hi I have a question", 3.0),
        ],
    }
    if start_ms is not None:
        payload["start_timestamp"] = start_ms
        payload["end_timestamp"] = start_ms + duration_ms
        payload["duration_ms"] = duration_ms
    payload.update(overrides)
    return payload
