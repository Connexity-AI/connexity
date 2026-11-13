"""Build what the single call shows from its stored trace."""

import json
import re

from pydantic import JsonValue
from sqlmodel import Session

from app import crud
from app.models.agent import Agent
from app.models.call import Call
from app.models.call_screen import (
    CallScreenEntry,
    CallScreenFinding,
    CallScreenPublic,
    KeyValue,
)
from app.models.enums import CallCheckStatus, CheckKind, FindingEffect, ToolCallStatus
from app.models.trace import ToolCallEvent, UtteranceEvent
from app.services.checks.registry import get_check

MASK = "••••"
_SECRET = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|authorization|auth|credential|^key$)",
    re.IGNORECASE,
)
_STATUS = {
    ToolCallStatus.OK: "ok",
    ToolCallStatus.ERROR: "failed",
    ToolCallStatus.TIMEOUT: "timed out",
    ToolCallStatus.NO_RESULT: "no result",
}


def mask_secrets(value: JsonValue, key: str = "") -> JsonValue:
    """Replace every value whose key looks secret with "••••", at any depth."""
    if key and _SECRET.search(key) and value not in (None, ""):
        return MASK
    if isinstance(value, dict):
        return {k: mask_secrets(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [mask_secrets(v, key) for v in value]
    return value


def _text(value: JsonValue) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _pairs(value: JsonValue) -> list[KeyValue]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return [KeyValue(key="text", value=value)]
    value = mask_secrets(value)
    if isinstance(value, dict):
        return [KeyValue(key=k, value=_text(v)) for k, v in value.items()]
    return [KeyValue(key="value", value=_text(value))]


def _seconds(ms: int | None) -> float:
    return round((ms or 0) / 1000, 3)


def _workflow_name(name: str | None, version: str | None) -> str | None:
    parts = [p for p in (name, f"v{version}" if version else None) if p]
    return " ".join(parts) or None


def call_screen(*, session: Session, call: Call) -> CallScreenPublic | None:
    """The single call as its screen shows it; ``None`` when it has no trace yet."""
    trace = crud.get_trace(session=session, call=call)
    if trace is None:
        return None
    agent = session.get(Agent, call.agent_id)
    workflows = {
        e.event_id: " · ".join(
            part
            for part in (
                _workflow_name(e.workflow_name, e.workflow_version),
                f"{len(e.steps)} steps" if e.steps else None,
            )
            if part
        )
        for e in crud.get_executions(session=session, call=call)
    }

    entries: list[CallScreenEntry] = []
    index_of: dict[str, int] = {}
    for event in trace.events:
        if isinstance(event, UtteranceEvent):
            index_of[event.id] = len(entries)
            entries.append(
                CallScreenEntry(
                    kind="turn",
                    at_seconds=_seconds(event.start_ms),
                    end_seconds=_seconds(event.end_ms)
                    if event.end_ms is not None
                    else None,
                    speaker=event.speaker.value,  # type: ignore[arg-type]
                    text=event.text,
                )
            )
        elif isinstance(event, ToolCallEvent):
            index_of[event.id] = len(entries)
            duration = None
            if event.start_ms is not None and event.end_ms is not None:
                duration = event.end_ms - event.start_ms
            entries.append(
                CallScreenEntry(
                    kind="tool",
                    at_seconds=_seconds(event.start_ms),
                    end_seconds=_seconds(event.end_ms)
                    if event.end_ms is not None
                    else None,
                    tool=event.name,
                    status=_STATUS.get(event.status) if event.status else None,  # type: ignore[arg-type]
                    duration_ms=duration,
                    arguments=_pairs(event.arguments),  # type: ignore[arg-type]
                    result=_pairs(event.result),
                    workflow=workflows.get(event.id) or None,
                )
            )

    categories = crud.categories_by_id(session=session)
    issues = {
        issue.id: issue for issue in crud.issues_of_findings(session=session, call=call)
    }
    findings: list[CallScreenFinding] = []
    for row in crud.get_findings(session=session, call=call):
        check = get_check(row.check_type)
        title = check.title if check else row.check_type
        issue = issues.get(row.issue_id)
        # Its moment is the last event it points at: for two bookings of one slot, the
        # second booking is where it went wrong.
        indexes = [index_of[e] for e in row.event_keys if e in index_of]
        index = max(indexes) if indexes else None
        at = entries[index].at_seconds if index is not None else 0.0
        findings.append(
            CallScreenFinding(
                id=row.id,
                at_seconds=at,
                text=f"{title}: {row.key}" if row.key else title,
                category=categories[issue.category_id].name if issue else "Other",
                severity="critical" if row.effect == FindingEffect.FAILS else "warning",
                found_by="rule" if row.kind == CheckKind.RULE else "model",
                entry_index=index,
            )
        )
        for key in row.event_keys:
            if key in index_of:
                entries[index_of[key]].finding_ids.append(row.id)
    findings.sort(key=lambda f: (f.severity != "critical", f.at_seconds))

    duration = None
    if call.ended_at is not None:
        duration = max(0, int((call.ended_at - call.started_at).total_seconds()))
    status = crud.call_check_statuses(session=session, call_ids=[call.id])[call.id]
    return CallScreenPublic(
        id=call.id,
        agent_id=call.agent_id,
        agent_name=agent.name if agent else "",
        started_at=call.started_at,
        duration_seconds=duration,
        caller_last_four=crud.caller_last_four(call.caller_number),
        result=status
        if isinstance(status, CallCheckStatus)
        else CallCheckStatus(status),
        version=call.agent_version,
        has_recording=bool(call.recording_url),
        entries=entries,
        findings=findings,
    )
