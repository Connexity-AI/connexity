"""Build what the single call shows from its stored trace."""

import json
import re
import uuid
from datetime import UTC, datetime

from pydantic import JsonValue
from sqlmodel import Session, select

from app import crud
from app.crud.spec import rules_of_specs
from app.crud.test_run import runs_of_agent
from app.models.agent import Agent
from app.models.call import Call
from app.models.call_screen import (
    CallScreenEntry,
    CallScreenFinding,
    CallScreenPublic,
    KeyValue,
    SimulatedLinePublic,
    SimulatedVerdictPublic,
)
from app.models.enums import (
    CallCheckStatus,
    CheckMode,
    FindingEffect,
    RuleOutcome,
    ToolCallStatus,
)
from app.models.run import Run
from app.models.schemas import ConversationTurn
from app.models.test_case import TestCase
from app.models.test_case_result import TestCaseResult
from app.models.test_run import RuleVerdict, SimulatedFinding
from app.models.trace import ToolCallEvent, Trace, UtteranceEvent
from app.services.checks.registry import get_check
from app.services.test_run import default_fake_calls, edited_runs, trace_of

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


def _entries(
    trace: Trace, workflows: dict[str, str]
) -> tuple[list[CallScreenEntry], dict[str, int]]:
    """The timeline: each utterance and tool call, and where each event sits in it."""
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
    return entries, index_of


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

    entries, index_of = _entries(trace, workflows)

    categories = crud.categories_by_id(session=session)

    issues = {
        issue.id: issue for issue in crud.issues_of_findings(session=session, call=call)
    }
    findings: list[CallScreenFinding] = []
    for row in crud.get_findings(session=session, call=call, shown_only=True):
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
                found_by=row.kind,
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


def simulated_call_screen(
    *, session: Session, result: TestCaseResult, run: Run
) -> CallScreenPublic:
    """A simulated call as the call screen shows it: the conversation, what code checks
    found in it, and the rules it was judged on with their verdicts.

    It has no recording, no timing and no caller. Its result comes from its verdicts
    and findings, so a call that failed a critical rule never reads Clean.
    """
    agent = session.get(Agent, run.agent_id)
    scenario = session.get(TestCase, result.test_case_id)
    transcript = [
        ConversationTurn.model_validate(turn) for turn in result.transcript or []
    ]
    started = _aware(result.started_at or result.created_at)
    defaults = default_fake_calls(transcript, scenario) if scenario else {}
    trace = trace_of(
        transcript, call_id=result.id, started_at=started, defaults=set(defaults)
    )
    entries, index_of = _entries(trace, {})

    categories = {c.key: c.name for c in crud.list_categories(session=session)}
    findings: list[CallScreenFinding] = []
    for n, raw in enumerate(result.check_findings or []):
        finding = SimulatedFinding.model_validate(raw)
        check = get_check(finding.check_type)
        title = check.title if check else finding.check_type
        finding_id = uuid.uuid5(result.id, str(n))
        indexes = [index_of[e] for e in finding.event_ids if e in index_of]
        index = max(indexes) if indexes else None
        findings.append(
            CallScreenFinding(
                id=finding_id,
                at_seconds=0.0,
                text=f"{title}: {finding.key}" if finding.key else title,
                category=categories.get(check.category, "Other") if check else "Other",
                severity="critical" if finding.mode == CheckMode.FAILS else "warning",
                found_by=finding.kind,
                entry_index=index,
            )
        )
        for key in finding.event_ids:
            if key in index_of:
                entries[index_of[key]].finding_ids.append(finding_id)
    findings.sort(key=lambda f: (f.severity != "critical", f.entry_index or 0))

    rules = (
        {
            rule.key: rule.text
            for rule in rules_of_specs(session=session, spec_ids=[run.spec_id]).get(
                run.spec_id, []
            )
        }
        if run.spec_id
        else {}
    )

    def entries_of(turns: list[int]) -> list[int]:
        out: list[int] = []
        for turn in turns:
            index = index_of.get(f"u{turn}", index_of.get(f"t{turn}-0"))
            if index is not None and index not in out:
                out.append(index)
        return out

    verdicts = sorted(
        session.exec(
            select(RuleVerdict).where(RuleVerdict.test_case_result_id == result.id)
        ).all(),
        key=lambda v: (
            v.outcome is not RuleOutcome.FAILED,
            v.outcome is RuleOutcome.DID_NOT_COME_UP,
            not v.critical,
            v.rule_key,
        ),
    )
    # A verdict that rests on a default fake is not evidence and fails nothing.
    failed = [v for v in verdicts if v.outcome is RuleOutcome.FAILED and v.mark is None]
    if not verdicts and not findings:
        status = CallCheckStatus.UNCHECKED
    elif any(v.critical for v in failed) or any(
        f.severity == "critical" for f in findings
    ):
        status = CallCheckStatus.FAILED
    elif failed or findings:
        status = CallCheckStatus.DEGRADED
    else:
        status = CallCheckStatus.CLEAN
    return CallScreenPublic(
        id=result.id,
        agent_id=run.agent_id,
        agent_name=agent.name if agent else "",
        started_at=started,
        result=status,
        version=run.platform_version,
        has_recording=False,
        entries=entries,
        findings=findings,
        simulated=SimulatedLinePublic(
            run_id=run.id,
            scenario_name=scenario.name if scenario else "",
            edited=run.id
            in edited_runs(runs_of_agent(session=session, agent_id=run.agent_id)),
            verdicts=[
                SimulatedVerdictPublic(
                    key=v.rule_key,
                    text=rules.get(v.rule_key),
                    critical=v.critical,
                    outcome=v.outcome,
                    reason=v.reason,
                    entry_indexes=entries_of(v.turns or []),
                )
                for v in verdicts
            ],
            stopped=result.error_message,
        ),
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)
