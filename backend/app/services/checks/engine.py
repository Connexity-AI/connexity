"""Run the checks over a stored call and keep what they find.

``run_checks`` is the pure part. ``check_call`` reads the call, decides what each check
was set to when the call started, and stores the result.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import Session

from app import crud
from app.models.call import Call
from app.models.check import DecisionRecord, Finding
from app.models.enums import CheckMode, FindingEffect
from app.models.execution import Execution
from app.models.trace import Trace
from app.services.checks.base import CheckInput, Fact, FactSource, Raised, RuleCheck
from app.services.checks.registry import CHECKS, FACT_SOURCES

logger = logging.getLogger(__name__)


class CheckError(Exception):
    """A check or a fact source did something it must not. A bug in it, not in the call."""


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def mode_at(
    check: RuleCheck, records: Sequence[DecisionRecord], moment: datetime
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


def current_mode(check: RuleCheck, records: Sequence[DecisionRecord]) -> CheckMode:
    """What ``check`` is set to now: its latest decision, whatever any clock says."""
    if not records:
        return check.default_mode
    return CheckMode(records[-1].new_value or check.default_mode)


@dataclass(frozen=True)
class CheckRun:
    found: list[tuple[RuleCheck, Raised]]
    # Checks that could not run, by type, with what went wrong.
    broken: dict[str, Exception]


def _validated(check: RuleCheck, raised: list[Raised], event_ids: set[str]) -> None:
    seen: set[tuple[str, ...]] = set()
    for item in raised:
        if not item.event_ids:
            msg = f"check '{check.type}' raised a finding that points at no event"
            raise CheckError(msg)
        if any(key not in event_ids for key in item.event_ids):
            msg = f"check '{check.type}' pointed at events the trace does not have"
            raise CheckError(msg)
        if item.event_ids in seen:
            msg = f"check '{check.type}' raised two findings on the same events"
            raise CheckError(msg)
        seen.add(item.event_ids)


def run_checks(
    *,
    trace: Trace,
    executions: list[Execution],
    checks: Sequence[RuleCheck],
    fact_sources: Sequence[FactSource] = (),
) -> CheckRun:
    """Run ``checks`` over one call. Pure: the same call gives the same findings.

    A check that raises is reported as broken and the others still run. So is one that
    asks for a fact nobody derives, points at an event the trace does not have, points
    at nothing, or raises the same finding twice (a ``CheckError``).
    """
    sources = {source.name: source for source in fact_sources}
    event_ids = {event.id for event in trace.events}
    derived: dict[str, list[Fact]] = {}
    run = CheckRun(found=[], broken={})
    for check in checks:
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
    checks: Sequence[RuleCheck] | None = None,
    fact_sources: Sequence[FactSource] | None = None,
) -> int | None:
    """Check ``call`` and replace its findings with what the checks raise now.

    Each check runs as it was set when the call started, so checking an old call again
    never changes what it counted for. A check that breaks is logged and keeps the
    findings it had; the others are stored, and the call is not noted as checked.

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
    effects: dict[str, FindingEffect] = {}
    for check in checks:
        mode = mode_at(check, history.get(check.type, []), started)
        if mode is not CheckMode.OFF:
            effects[check.type] = FindingEffect(mode.value)

    run = run_checks(
        trace=trace,
        executions=crud.get_executions(session=session, call=call),
        checks=[check for check in checks if check.type in effects],
        fact_sources=fact_sources,
    )
    for check_type, error in run.broken.items():
        logger.error("Check '%s' broke on call %s", check_type, call.id, exc_info=error)
    return crud.replace_findings(
        session=session,
        call=call,
        check_types={check.type for check in checks} - set(run.broken),
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
                effect=effects[check.type],
                retroactive=started < existed_since[check.type],
            )
            for check, raised in run.found
        ],
        checked=not run.broken,
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
