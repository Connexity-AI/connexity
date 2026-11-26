"""Ask the models for model checks (classifiers and judges) and check those calls again.

``check_call`` records a model check without a stored answer as pending. A pass here
takes the newest pending calls, asks each check's model once (``ModelCheck.ask``),
stores the answer, or a failed attempt, and checks the call again, which now turns
the answer into findings.

It runs in the scheduled call pull (every minute, inside its request, because Cloud
Run gives CPU only while it answers) and within the product's daily model budget,
``MODEL_CHECKS_DAILY_BUDGET_USD``: once today's spend (UTC) reaches it, nothing more
is asked until tomorrow, and the calls stay pending.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import JsonValue
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models.call import Call
from app.models.enums import ModelAnswerStatus
from app.models.trace import Trace
from app.services.checks.base import ModelCheck, ModelReply
from app.services.checks.engine import check_call
from app.services.checks.providers import keys_present, missing_key
from app.services.checks.registry import CHECKS
from app.services.jev import JevError

logger = logging.getLogger(__name__)

# Calls asked about in one pass. Each may be several model requests (Jev asks per turn).
MAX_CALLS_PER_PASS = 50


@dataclass
class ModelPass:
    answered: int = 0
    failed: int = 0
    # Waiting calls not asked about: the budget ran out, or the pass's time did.
    left: int = 0
    spent_usd: float = 0.0
    budget_reached: bool = False


def _day_start(now: datetime) -> datetime:
    return now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _error(exc: BaseException) -> str:
    # Never the message itself: a provider's error can quote the request, which holds
    # what was said on the call.
    if isinstance(exc, JevError) and exc.status is not None:
        return f"{type(exc).__name__} {exc.status}"
    return type(exc).__name__


def model_checks() -> dict[str, ModelCheck]:
    return {check.type: check for check in CHECKS if isinstance(check, ModelCheck)}


async def answer_model_checks(
    *,
    session: Session,
    agent_ids: list[uuid.UUID] | None = None,
    limit: int = MAX_CALLS_PER_PASS,
    deadline: float | None = None,
    checks: dict[str, ModelCheck] | None = None,
) -> ModelPass:
    """Ask the models about calls waiting for them, newest first, and check those
    calls again. Stops at ``limit`` calls, at ``deadline`` (a ``time.monotonic()``
    value) or at the daily budget. Never raises for one call's failure.
    """
    checks = model_checks() if checks is None else checks
    result = ModelPass()
    if not checks:
        return result
    budget = settings.MODEL_CHECKS_DAILY_BUDGET_USD
    spent = crud.model_spend_since(session=session, since=_day_start(datetime.now(UTC)))
    if spent >= budget:
        result.budget_reached = True
        return result
    waiting = [
        (call, checks[check_type])
        for call, check_type in crud.calls_waiting_for_models(
            session=session,
            versions={check.type: check.version for check in checks.values()},
            agent_ids=agent_ids,
            limit=limit,
            keys_present=keys_present(),
        )
        if missing_key(checks[check_type].provider) is None
    ]
    jobs: list[tuple[Call, ModelCheck, Trace, JsonValue]] = []
    for call, check in waiting:
        trace = crud.get_trace(session=session, call=call)
        if trace is not None:
            # Read before asking, while this pass holds the session: what the check
            # needs beyond the trace (the spec check: the rules and the call's inputs).
            prepared = check.prepare(session, call) if check.prepare else None
            jobs.append((call, check, trace, prepared))

    limiter = asyncio.Semaphore(settings.MODEL_CHECK_CONCURRENCY)

    async def ask(
        check: ModelCheck, trace: Trace, prepared: JsonValue
    ) -> ModelReply | BaseException | None:
        nonlocal spent
        async with limiter:
            if spent >= budget:
                result.budget_reached = True
                return None
            left = None if deadline is None else deadline - time.monotonic()
            if left is not None and left <= 0:
                return None
            try:
                # Never past the pass's deadline: the pull answers inside its request.
                reply = await asyncio.wait_for(check.ask(trace, prepared), timeout=left)
            except TimeoutError:
                # Out of time, not a failure: the call waits for the next pass.
                return None
            except Exception as exc:  # noqa: BLE001 - recorded as a failed attempt
                return exc
            spent += reply.cost_usd
            return reply

    replies = await asyncio.gather(
        *(ask(check, trace, prepared) for _, check, trace, prepared in jobs)
    )

    for (call, check, _, _), reply in zip(jobs, replies, strict=True):
        if reply is None:
            result.left += 1
            continue
        if isinstance(reply, BaseException):
            logger.warning(
                "Model check '%s' could not ask about call %s: %s",
                check.type,
                call.id,
                _error(reply),
            )
            crud.save_model_answer(
                session=session,
                call=call,
                check_type=check.type,
                check_version=check.version,
                status=ModelAnswerStatus.FAILED,
                model=check.model,
                error=_error(reply),
            )
            result.failed += 1
        else:
            crud.save_model_answer(
                session=session,
                call=call,
                check_type=check.type,
                check_version=check.version,
                status=ModelAnswerStatus.OK,
                model=reply.model,
                answer=reply.answer,
                input_tokens=reply.input_tokens,
                output_tokens=reply.output_tokens,
                requests=reply.requests,
                cost_usd=reply.cost_usd,
            )
            result.answered += 1
            result.spent_usd += reply.cost_usd
        # Turns the answer into findings, or records the check as broke once it has
        # failed too often. Only this check: the others already ran on the call.
        try:
            check_call(session=session, call=call, checks=[check])
        except Exception:  # noqa: BLE001 - the answer is stored; the next pass retries
            session.rollback()
            logger.exception("Call %s could not be checked again", call.id)
    return result
