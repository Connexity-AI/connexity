"""Run the checks over a stored call and keep what they find.

``run_checks`` is the pure part. ``check_call`` reads the call, decides what each check
was set to when the call started, and stores the result.

A model check (classifier or judge) runs here only once its model's answer is stored
(`ModelAnswer`); until then it is recorded as pending and keeps the findings it had.
``model_checks.answer_model_checks`` asks the models and checks those calls again.
"""

import logging
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import JsonValue
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.db import engine
from app.models.call import Call
from app.models.check import CallCheck, DecisionRecord, Finding
from app.models.enums import (
    CheckMode,
    CheckOutcome,
    FindingEffect,
    ModelAnswerStatus,
)
from app.models.execution import Execution
from app.models.trace import Trace
from app.services.checks.base import (
    Check,
    CheckInput,
    Fact,
    FactSource,
    ModelCheck,
    Raised,
)
from app.services.checks.providers import missing_key
from app.services.checks.registry import CHECKS, FACT_SOURCES
from app.services.trace_capabilities import derive_capabilities

logger = logging.getLogger(__name__)


class CheckError(Exception):
    """A check or a fact source did something it must not. A bug in it, not in the call."""


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def mode_at(
    check: Check, records: Sequence[DecisionRecord], moment: datetime
) -> CheckMode:
    """What ``check`` was set to at ``moment``.

    ``records`` are the setting changes for this check and one agent, oldest first. A
    decision takes effect when it is made, so a moment before the first change has the
    value that change replaced.
    """
    if not records:
        return check.default_mode
    mode = CheckMode(records[0].old_value or check.default_mode)
    for record in records:
        if _aware(record.created_at) > moment:
            break
        mode = CheckMode(record.new_value or check.default_mode)
    return mode


def current_mode(check: Check, records: Sequence[DecisionRecord]) -> CheckMode:
    """What ``check`` is set to now: its latest decision, whatever any clock says."""
    if not records:
        return check.default_mode
    return CheckMode(records[-1].new_value or check.default_mode)


@dataclass(frozen=True)
class CheckRun:
    found: list[tuple[Check, Raised]]
    # Checks that could not run, by type, with what went wrong.
    broken: dict[str, Exception]


def _validated(check: Check, raised: list[Raised], event_ids: set[str]) -> None:
    seen: set[tuple[str | None, tuple[str, ...]]] = set()
    for item in raised:
        if not item.event_ids and not check.whole_call:
            msg = f"check '{check.type}' raised a finding that points at no event"
            raise CheckError(msg)
        if check.whole_call and (item.event_ids or not item.key):
            msg = f"check '{check.type}' judges the whole call: no events, and a key"
            raise CheckError(msg)
        if any(key not in event_ids for key in item.event_ids):
            msg = f"check '{check.type}' pointed at events the trace does not have"
            raise CheckError(msg)
        identity = (item.key if check.whole_call else None, item.event_ids)
        if identity in seen:
            msg = f"check '{check.type}' raised two findings on the same events"
            raise CheckError(msg)
        seen.add(identity)


def run_checks(
    *,
    trace: Trace,
    executions: list[Execution],
    checks: Sequence[Check],
    fact_sources: Sequence[FactSource] = (),
    answers: Mapping[str, JsonValue] | None = None,
) -> CheckRun:
    """Run ``checks`` over one call. Pure: the same call gives the same findings.

    A model check runs only with its model's answer in ``answers`` (by check type);
    without one it is left out, neither run nor broken.

    A check that raises is reported as broken and the others still run. So is one that
    asks for a fact nobody derives, points at an event the trace does not have, points
    at nothing, or raises the same finding twice (a ``CheckError``).
    """
    answers = answers or {}
    sources = {source.name: source for source in fact_sources}
    event_ids = {event.id for event in trace.events}
    derived: dict[str, list[Fact]] = {}
    run = CheckRun(found=[], broken={})
    for check in checks:
        if isinstance(check, ModelCheck) and check.type not in answers:
            continue
        try:
            for name in check.facts:
                if name in derived:
                    continue
                source = sources.get(name)
                if source is None:
                    msg = (
                        f"check '{check.type}' needs fact '{name}', "
                        "which nothing derives"
                    )
                    raise CheckError(msg)
                derived[name] = source.derive(trace, executions)
            raised = check.run(
                CheckInput(
                    trace=trace,
                    executions=executions,
                    facts={name: derived[name] for name in check.facts},
                    answer=answers.get(check.type),
                )
            )
            _validated(check, raised, event_ids)
        except Exception as exc:  # noqa: BLE001 - one check's bug must not stop the rest
            run.broken[check.type] = exc
            continue
        run.found.extend((check, item) for item in raised)
    return run


def record_check_releases(session: Session) -> None:
    """Note the checks this server carries, so later calls know they existed."""
    crud.ensure_check_releases(
        session=session, versions={check.type: check.version for check in CHECKS}
    )


def check_call(
    *,
    session: Session,
    call: Call,
    checks: Sequence[Check] | None = None,
    fact_sources: Sequence[FactSource] | None = None,
) -> int | None:
    """Check ``call`` and replace its findings with what the checks raise now.

    Each check runs as it was set when the call started, so checking an old call again
    never changes what it counted for. What each check did (ran, skipped, broke, off,
    pending) is recorded for the call. A check that breaks is logged and keeps the
    findings it had, and so does a model check still waiting for its answer; the
    others are stored.

    Returns:
        How many findings the checks that ran raised, or ``None`` when the call has
        no trace.
    """
    if call.schema_version is None:
        return None
    checks = CHECKS if checks is None else checks
    fact_sources = FACT_SOURCES if fact_sources is None else fact_sources
    # Before the lock: recording a release commits, which would let the lock go.
    existed_since = crud.ensure_check_releases(
        session=session, versions={check.type: check.version for check in checks}
    )

    call = crud.lock_call(session=session, call_id=call.id)
    trace = crud.get_trace(session=session, call=call)
    if trace is None:
        session.rollback()
        return None
    started = _aware(call.started_at)
    history = crud.check_setting_history(session=session, agent_id=call.agent_id)
    capabilities = set(derive_capabilities(trace))
    stored_answers = crud.get_model_answers(
        session=session,
        call_id=call.id,
        versions={
            check.type: check.version
            for check in checks
            if isinstance(check, ModelCheck)
        },
    )
    effects: dict[str, FindingEffect] = {}
    outcomes: dict[str, tuple[CheckOutcome, str | None]] = {}
    answers: dict[str, JsonValue] = {}
    # Findings on a call that started before this count for nothing: the check's
    # release, or what its ``applies`` says.
    counts_from = {check.type: existed_since[check.type] for check in checks}
    # Model checks that keep the findings they had: waiting, or failed for good.
    kept: set[str] = set()
    for check in checks:
        mode = mode_at(check, history.get(check.type, []), started)
        missing = [need.value for need in check.needs if need not in capabilities]
        applies = None
        if mode is not CheckMode.OFF and not missing and check.applies is not None:
            applies = check.applies(session, call, existed_since[check.type])
            if applies.counts_from is not None:
                counts_from[check.type] = applies.counts_from
        if mode is CheckMode.OFF:
            outcomes[check.type] = (CheckOutcome.OFF, None)
        elif missing:
            outcomes[check.type] = (CheckOutcome.SKIPPED, ", ".join(missing))
        elif applies is not None and applies.skip is not None:
            outcomes[check.type] = (CheckOutcome.SKIPPED, applies.skip)
        elif isinstance(check, ModelCheck):
            stored = stored_answers.get(check.type)
            no_key = missing_key(check.provider)
            if stored is not None and stored.status is ModelAnswerStatus.OK:
                answers[check.type] = stored.answer
                effects[check.type] = FindingEffect(mode.value)
            elif no_key is not None:
                outcomes[check.type] = (CheckOutcome.SKIPPED, no_key)
            elif (
                stored is not None
                and stored.attempts >= settings.MODEL_CHECK_MAX_ATTEMPTS
            ):
                outcomes[check.type] = (CheckOutcome.BROKE, None)
                kept.add(check.type)
            else:
                outcomes[check.type] = (CheckOutcome.PENDING, None)
                kept.add(check.type)
        else:
            effects[check.type] = FindingEffect(mode.value)

    run = run_checks(
        trace=trace,
        executions=crud.get_executions(session=session, call=call),
        checks=[check for check in checks if check.type in effects],
        fact_sources=fact_sources,
        answers=answers,
    )
    for check_type, error in run.broken.items():
        logger.error("Check '%s' broke on call %s", check_type, call.id, exc_info=error)
    for check_type in effects:
        outcome = CheckOutcome.BROKE if check_type in run.broken else CheckOutcome.RAN
        outcomes[check_type] = (outcome, None)
    return crud.replace_findings(
        session=session,
        call=call,
        categories={check.type: check.category for check in checks},
        issue_categories={
            (check.type, raised.key or ""): raised.category
            for check, raised in run.found
            if raised.category is not None
        },
        subjects={
            (check.type, raised.key or ""): raised.subject
            for check, raised in run.found
            if raised.subject is not None
        },
        # A broken check keeps the findings it had: the fault is ours, not the call's.
        check_types={check.type for check in checks} - set(run.broken) - kept,
        findings=[
            Finding(
                company_id=call.company_id,
                agent_id=call.agent_id,
                call_id=call.id,
                check_type=check.type,
                check_version=check.version,
                kind=check.kind,
                key=raised.key,
                event_keys=list(raised.event_ids),
                detail=raised.detail,
                effect=FindingEffect.FLAGS
                if raised.flags_only
                else effects[check.type],
                retroactive=started < _aware(counts_from[check.type]),
            )
            for check, raised in run.found
        ],
        runs=[
            CallCheck(
                call_id=call.id,
                check_type=check.type,
                company_id=call.company_id,
                check_version=check.version,
                outcome=outcomes[check.type][0],
                missing=outcomes[check.type][1],
            )
            for check in checks
        ],
    )


def check_call_safely(*, session: Session, call: Call) -> int | None:
    """As ``check_call``, but never raises: storing a call must not fail because it
    could not be checked. The call is then left as it was."""
    call_id = call.id
    try:
        return check_call(session=session, call=call)
    except Exception:  # noqa: BLE001 - the call is already stored; log and move on
        session.rollback()
        logger.exception("Call %s could not be checked", call_id)
        return None


def is_loosening(old: CheckMode, new: CheckMode) -> bool:
    """Whether the change can only make reliability or quality look better."""
    order: Mapping[CheckMode, int] = {
        CheckMode.OFF: 0,
        CheckMode.FLAGS: 1,
        CheckMode.FAILS: 2,
    }
    return order[new] < order[old]


# Stored calls checked in one pass. A pass is cheap (no network), so this only bounds
# how long one request or background task holds a database session.
MAX_CALLS_PER_PASS = 200


def check_calls_needing_it(
    *,
    session: Session,
    agent_ids: list[uuid.UUID],
    limit: int = MAX_CALLS_PER_PASS,
    deadline: float | None = None,
) -> int:
    """Check these agents' stored calls that some current check version never ran on,
    newest first: calls stored before a check existed, or checked by an older version
    of it (which is also how a call a check broke on is tried again with its fix).

    Stops at ``limit`` calls or at ``deadline`` (a ``time.monotonic()`` value). A call
    is picked up once per version: after this it has a run of every current check,
    whatever the outcome. Findings on calls that started before a check existed are
    retroactive.

    Returns:
        How many calls were checked.
    """
    versions = {check.type: check.version for check in CHECKS}
    checked = 0
    for call in crud.calls_needing_checks(
        session=session, agent_ids=agent_ids, versions=versions, limit=limit
    ):
        if deadline is not None and time.monotonic() >= deadline:
            break
        call_id, company_id = call.id, call.company_id
        if check_call_safely(session=session, call=call) is not None:
            checked += 1
            continue
        # The call could not be checked at all. Say so, or every pass would pick it up
        # again and never reach the calls behind it.
        crud.record_checks_broke(
            session=session, call_id=call_id, company_id=company_id, versions=versions
        )
    return checked


def count_calls_needing_it(*, session: Session, agent_id: uuid.UUID) -> int:
    return crud.count_calls_needing_checks(
        session=session,
        agent_ids=[agent_id],
        versions={check.type: check.version for check in CHECKS},
    )


def check_unchecked_calls_in_background(agent_id: uuid.UUID) -> None:
    """For a worker thread: its own database session, never raises."""
    try:
        with Session(engine) as session:
            check_calls_needing_it(session=session, agent_ids=[agent_id])
    except Exception:  # noqa: BLE001 - a background task has no one to raise to
        logger.exception("Stored calls of agent %s could not be checked", agent_id)
