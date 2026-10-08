"""Retell call payload -> Connexity trace.

Built from Retell's documented call object and checked against the shape of real calls.
Two things real payloads have that the documentation does not show: tool invocations,
node transitions and keypad presses carry ``time_sec``; and adjacent timeline items are
not always in time order (overlapping speech), so events are sorted by start time here.
"""

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import JsonValue

from app.models.enums import (
    CallChannel,
    CallDirection,
    CallEndReason,
    Speaker,
    ToolCallStatus,
)
from app.models.trace import (
    EVENT_ID_MAX_LENGTH,
    MarkerEvent,
    ToolCallEvent,
    Trace,
    TraceComponent,
    TraceEvent,
    TraceParties,
    UtteranceEvent,
)

PROVIDER = "retell"


class RetellMappingError(ValueError):
    """The payload cannot be turned into a trace (for example it has no timestamps)."""


_SPEAKERS: dict[str, Speaker] = {
    "agent": Speaker.AGENT,
    "user": Speaker.CALLER,
    "transfer_target": Speaker.OTHER,
}

_CHANNELS: dict[str, CallChannel] = {
    "phone_call": CallChannel.PHONE,
    "web_call": CallChannel.WEB,
}

# Retell's disconnection reasons, grouped onto the trace's fixed list. A reason Retell
# adds later falls through to UNKNOWN; its text is always kept in end_reason_detail.
_END_REASONS: dict[str, CallEndReason] = {
    "user_hangup": CallEndReason.CALLER_HANGUP,
    "user_declined": CallEndReason.CALLER_HANGUP,
    "user_requested_dnc": CallEndReason.CALLER_HANGUP,
    "user_requested_callback": CallEndReason.CALLER_HANGUP,
    "agent_hangup": CallEndReason.AGENT_HANGUP,
    "manual_stopped": CallEndReason.AGENT_HANGUP,
    "call_transfer": CallEndReason.TRANSFER,
    "transfer_bridged": CallEndReason.TRANSFER,
    "transfer_cancelled": CallEndReason.TRANSFER,
    "call_take_over": CallEndReason.TRANSFER,
    "voicemail_reached": CallEndReason.VOICEMAIL,
    "ivr_reached": CallEndReason.VOICEMAIL,
    "dial_busy": CallEndReason.NO_ANSWER,
    "dial_failed": CallEndReason.NO_ANSWER,
    "dial_no_answer": CallEndReason.NO_ANSWER,
    "invalid_destination": CallEndReason.NO_ANSWER,
    "marked_as_spam": CallEndReason.NO_ANSWER,
    "network_blocked": CallEndReason.NO_ANSWER,
    "registered_call_timeout": CallEndReason.NO_ANSWER,
    "error_user_not_joined": CallEndReason.NO_ANSWER,
    "inactivity": CallEndReason.LIMIT,
    "max_duration_reached": CallEndReason.LIMIT,
    "concurrency_limit_reached": CallEndReason.ERROR,
    "no_concurrency_fallback": CallEndReason.ERROR,
    "no_valid_payment": CallEndReason.ERROR,
    "credit_exhausted": CallEndReason.ERROR,
    "budget_reached": CallEndReason.ERROR,
    "scam_detected": CallEndReason.ERROR,
    "telephony_provider_permission_denied": CallEndReason.ERROR,
    "telephony_provider_unavailable": CallEndReason.ERROR,
    "sip_routing_error": CallEndReason.ERROR,
    "error_llm_websocket_open": CallEndReason.ERROR,
    "error_llm_websocket_lost_connection": CallEndReason.ERROR,
    "error_llm_websocket_runtime": CallEndReason.ERROR,
    "error_llm_websocket_corrupt_payload": CallEndReason.ERROR,
    "error_no_audio_received": CallEndReason.ERROR,
    "error_asr": CallEndReason.ERROR,
    "error_retell": CallEndReason.ERROR,
    "error_unknown": CallEndReason.ERROR,
}

# Copied into ``extensions`` when present: useful, but with no field of their own.
_EXTENSION_KEYS = (
    "call_status",
    "duration_ms",
    "latency",
    "call_cost",
    "llm_token_usage",
    "metadata",
    "public_log_url",
    "transfer_destination",
    "telephony_identifier",
    "agent_tag",
)


def _as_json(value: Any) -> JsonValue:
    # Payloads arrive as parsed JSON, so every value already is a JSON value.
    return value


def _ms(seconds: Any) -> int | None:
    if isinstance(seconds, bool) or not isinstance(seconds, int | float):
        return None
    return max(0, round(seconds * 1000))


def _timestamp(epoch_ms: Any) -> datetime | None:
    if isinstance(epoch_ms, bool) or not isinstance(epoch_ms, int | float):
        return None
    return datetime.fromtimestamp(epoch_ms / 1000, tz=UTC)


def _parse_json(text: Any) -> JsonValue:
    """Parsed JSON when ``text`` is a JSON string; otherwise the value unchanged."""
    if not isinstance(text, str):
        return _as_json(text)
    try:
        return _as_json(json.loads(text))
    except ValueError:
        return text


def _arguments(raw: Any) -> dict[str, JsonValue] | None:
    parsed = _parse_json(raw)
    if parsed is None or parsed == "":
        return None
    if isinstance(parsed, dict):
        return parsed
    # Arguments that are not an object are kept, not dropped.
    return {"value": parsed}


def _word_span(item: dict[str, Any]) -> tuple[int | None, int | None]:
    words = [w for w in item.get("words") or [] if isinstance(w, dict)]
    starts = [ms for w in words if (ms := _ms(w.get("start"))) is not None]
    ends = [ms for w in words if (ms := _ms(w.get("end"))) is not None]
    start = min(starts) if starts else _ms(item.get("time_sec"))
    end = max(ends) if ends else None
    if start is None or (end is not None and end < start):
        end = None
    return start, end


def _events(items: list[Any]) -> list[TraceEvent]:
    """Timeline items -> events, ordered by start time, tool results joined to calls."""
    results: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and item.get("role") == "tool_call_result":
            call_id = item.get("tool_call_id")
            if isinstance(call_id, str):
                results[call_id] = item

    drafts: list[tuple[int | None, dict[str, Any]]] = []
    joined: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role in _SPEAKERS:
            start, end = _word_span(item)
            drafts.append(
                (
                    start,
                    {
                        "kind": "utterance",
                        "speaker": _SPEAKERS[role],
                        "text": str(item.get("content") or ""),
                        "end_ms": end,
                    },
                )
            )
        elif role == "tool_call_invocation":
            call_id = item.get("tool_call_id")
            result = results.get(call_id) if isinstance(call_id, str) else None
            start = _ms(item.get("time_sec"))
            end = _ms(result.get("time_sec")) if result else None
            if start is None or (end is not None and end < start):
                end = None
            if result is None:
                status = ToolCallStatus.NO_RESULT
            elif result.get("successful") is False:
                status = ToolCallStatus.ERROR
            else:
                status = ToolCallStatus.OK
            if isinstance(call_id, str) and result is not None:
                joined.add(call_id)
            drafts.append(
                (
                    start,
                    {
                        "kind": "tool_call",
                        "tool_call_id": call_id,
                        "name": str(item.get("name") or "unknown_tool"),
                        "arguments": _arguments(item.get("arguments")),
                        "status": status,
                        "result": _parse_json(result.get("content"))
                        if result
                        else None,
                        "end_ms": end,
                    },
                )
            )
        elif role == "tool_call_result":
            call_id = item.get("tool_call_id")
            if isinstance(call_id, str) and call_id in joined:
                continue
            has_invocation = any(
                isinstance(other, dict)
                and other.get("role") == "tool_call_invocation"
                and other.get("tool_call_id") == call_id
                for other in items
            )
            if has_invocation:
                continue
            # A result whose invocation Retell did not log: keep it as its own call.
            drafts.append(
                (
                    _ms(item.get("time_sec")),
                    {
                        "kind": "tool_call",
                        "tool_call_id": call_id,
                        "name": "unknown_tool",
                        "arguments": None,
                        "status": ToolCallStatus.ERROR
                        if item.get("successful") is False
                        else ToolCallStatus.OK,
                        "result": _parse_json(item.get("content")),
                        "end_ms": None,
                    },
                )
            )
        else:
            detail = {
                key: _as_json(value)
                for key, value in item.items()
                if key not in ("role", "time_sec")
            }
            drafts.append(
                (
                    _ms(item.get("time_sec")),
                    {
                        "kind": "marker",
                        "name": str(role or "unknown"),
                        "detail": detail or None,
                    },
                )
            )

    # Order by start time. An item with no time stays right after the item before it.
    keyed: list[tuple[int, int, int | None, dict[str, Any]]] = []
    last_key = 0
    for position, (start, draft) in enumerate(drafts):
        sort_key = start if start is not None else last_key
        last_key = sort_key
        keyed.append((sort_key, position, start, draft))
    keyed.sort(key=lambda entry: (entry[0], entry[1]))

    events: list[TraceEvent] = []
    used_ids: set[str] = set()
    for number, (_, _, start, draft) in enumerate(keyed, start=1):
        event_id = f"e{number}"
        if draft["kind"] == "tool_call":
            # Keep Retell's own id when it is usable: it is what a backend log refers to.
            tool_call_id = draft["tool_call_id"]
            if (
                isinstance(tool_call_id, str)
                and 0 < len(tool_call_id) <= EVENT_ID_MAX_LENGTH
                and tool_call_id not in used_ids
            ):
                event_id = tool_call_id
        used_ids.add(event_id)

        if draft["kind"] == "utterance":
            events.append(
                UtteranceEvent(
                    id=event_id,
                    speaker=draft["speaker"],
                    text=draft["text"],
                    start_ms=start,
                    end_ms=draft["end_ms"],
                )
            )
        elif draft["kind"] == "tool_call":
            events.append(
                ToolCallEvent(
                    id=event_id,
                    name=draft["name"][:255],
                    arguments=draft["arguments"],
                    status=draft["status"],
                    result=draft["result"],
                    start_ms=start,
                    end_ms=draft["end_ms"],
                )
            )
        else:
            events.append(
                MarkerEvent(
                    id=event_id,
                    name=draft["name"][:255],
                    detail=draft["detail"],
                    start_ms=start,
                )
            )
    return events


def _parties(payload: dict[str, Any]) -> TraceParties | None:
    from_number = payload.get("from_number")
    to_number = payload.get("to_number")
    if payload.get("direction") == "outbound":
        agent_number, caller_number = from_number, to_number
    else:
        agent_number, caller_number = to_number, from_number
    if not agent_number and not caller_number:
        return None
    return TraceParties(
        agent_number=str(agent_number) if agent_number else None,
        caller_number=str(caller_number) if caller_number else None,
    )


def _recording_url(payload: dict[str, Any]) -> str | None:
    url = payload.get("recording_url")
    # An over-long (for example signed) link stays in the original payload only.
    if not isinstance(url, str) or not url or len(url) > 2048:
        return None
    return url


def _outputs(payload: dict[str, Any]) -> dict[str, JsonValue] | None:
    outputs: dict[str, JsonValue] = {}
    analysis = payload.get("call_analysis")
    if isinstance(analysis, dict):
        outputs.update({key: _as_json(value) for key, value in analysis.items()})
    collected = payload.get("collected_dynamic_variables")
    if isinstance(collected, dict) and collected:
        outputs["collected_dynamic_variables"] = _as_json(collected)
    return outputs or None


def retell_call_to_trace(payload: dict[str, Any]) -> Trace:
    """Convert one Retell call object (from the API or a webhook) into a trace.

    Raises:
        RetellMappingError: The payload has no call id or no usable timestamp.
    """
    call_id = payload.get("call_id")
    if not isinstance(call_id, str) or not call_id:
        msg = "Retell payload has no call_id"
        raise RetellMappingError(msg)

    ended_at = _timestamp(payload.get("end_timestamp"))
    # A call that never connected has no start; it is placed at the moment it ended.
    started_at = _timestamp(payload.get("start_timestamp")) or ended_at
    if started_at is None:
        msg = f"Retell call {call_id} has neither start_timestamp nor end_timestamp"
        raise RetellMappingError(msg)
    if ended_at is not None and ended_at < started_at:
        ended_at = None

    timeline = payload.get("transcript_with_tool_calls")
    if not isinstance(timeline, list):
        # Older or trimmed payloads carry speech only.
        timeline = payload.get("transcript_object")
    events = _events(timeline if isinstance(timeline, list) else [])

    reason = payload.get("disconnection_reason")
    end_reason: CallEndReason | None = None
    if isinstance(reason, str) and reason:
        end_reason = _END_REASONS.get(reason, CallEndReason.UNKNOWN)

    components: list[TraceComponent] = []
    agent_id = payload.get("agent_id")
    if isinstance(agent_id, str) and agent_id:
        version = payload.get("agent_version")
        components.append(
            TraceComponent(
                kind="agent",
                name=str(payload.get("agent_name") or agent_id)[:255],
                ref=agent_id,
                version=str(version) if version is not None else None,
            )
        )

    inputs = payload.get("retell_llm_dynamic_variables")
    direction = payload.get("direction")
    extensions = {
        key: _as_json(payload[key]) for key in _EXTENSION_KEYS if payload.get(key)
    }

    return Trace(
        provider=PROVIDER,
        external_id=call_id,
        started_at=started_at,
        channel=_CHANNELS.get(str(payload.get("call_type"))),
        direction=CallDirection(direction)
        if direction in (CallDirection.INBOUND, CallDirection.OUTBOUND)
        else None,
        ended_at=ended_at,
        end_reason=end_reason,
        end_reason_detail=reason[:255] if isinstance(reason, str) and reason else None,
        parties=_parties(payload),
        recording_url=_recording_url(payload),
        inputs={key: _as_json(value) for key, value in inputs.items()}
        if isinstance(inputs, dict)
        else None,
        components=components or None,
        # Retell logs every tool call in the timeline, so none means none were made.
        reports_tool_calls=True,
        events=events,
        outputs=_outputs(payload),
        extensions=extensions or None,
    )
