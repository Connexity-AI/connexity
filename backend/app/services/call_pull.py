"""The scheduled call pull: the main way new calls reach Connexity.

Cloud Scheduler calls the pull every minute (`POST /api/v1/internal/calls/pull`). The
work happens inside that request, because Cloud Run gives CPU only while it answers.
See `docs-internal/call-ingestion.md`.

A run, one at a time (a lease row in the database):

1. Works per Retell account (one API key, which several workspaces may hold), oldest
   pulled first. A paused account waits; an idle one (no call in the last hour) is
   pulled every 10 minutes.
2. Lists the account's added agents' calls that started after its position, in one
   request, oldest first. Calls already stored are skipped. Each new call that has
   ended is read in full and stored in every workspace that added its agent, through
   the webhook's path. The position stops just before a call still in progress.
3. Reads again, once, calls stored without Retell's post-call analysis.
4. Stops at `MAX_READS` full reads or `RUN_SECONDS`. A 429 or another failure pauses
   that account with a growing wait; the other accounts carry on.

Storing is idempotent, so the pull, the webhook and the first scan never duplicate a
call.
"""

import logging
import random
import time
import uuid
from datetime import UTC, datetime, timedelta

from cryptography.fernet import InvalidToken
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, func, select

from app import crud
from app.core.encryption import decrypt
from app.models.agent import Agent
from app.models.call import Call
from app.models.call_pull import CallPullAccount, CallPullLease
from app.models.enums import IntegrationProvider
from app.models.integration import Integration
from app.services.call_sync import emit, store_retell_calls
from app.services.retell import (
    RetellCallSummary,
    RetellRateLimited,
    get_retell_call,
    list_retell_call_summaries,
)

logger = logging.getLogger(__name__)

# Full call reads in one run, across all accounts: a backlog drains over several runs.
MAX_READS = 50
# Work in one run, below Cloud Scheduler's 60-second deadline.
RUN_SECONDS = 45.0
LIST_LIMIT = 1000
LEASE = timedelta(minutes=2)
IDLE_AFTER = timedelta(hours=1)
IDLE_EVERY = timedelta(minutes=10)
# Retell's longest call is two hours: a call still "in progress" after that never ends.
STUCK_AFTER = timedelta(hours=2)
# Post-call analysis arrives shortly after a call ends.
REREAD_AFTER = timedelta(minutes=2)
REREAD_WITHIN = timedelta(days=1)
# Failed runs in a row after which a call Retell keeps failing to return is passed over.
POISON_AFTER = 3
BACKOFF_START = timedelta(minutes=1)
BACKOFF_MAX = timedelta(minutes=10)


class PullRun(BaseModel):
    status: str
    accounts_pulled: int = 0
    calls_stored: int = 0
    calls_reread: int = 0
    reads: int = 0
    skipped: dict[str, int] = {}


class _Budget:
    def __init__(self) -> None:
        self.deadline = time.monotonic() + RUN_SECONDS
        self.reads = 0

    def can_read(self) -> bool:
        return self.reads < MAX_READS and time.monotonic() < self.deadline


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _from_ms(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


# ── The lease ──────────────────────────────────────────────────────────────


def take_lease(*, session: Session, holder: str, now: datetime) -> bool:
    """Take the run lease if it is free or expired. One statement, so two runs that
    start together cannot both get it."""
    session.execute(
        pg_insert(CallPullLease)
        .values(id=1, held_until=now - timedelta(seconds=1), holder="")
        .on_conflict_do_nothing(index_elements=["id"])
    )
    taken = session.execute(
        update(CallPullLease)
        .where(col(CallPullLease.id) == 1, col(CallPullLease.held_until) < now)
        .values(held_until=now + LEASE, holder=holder)
        .returning(col(CallPullLease.id))
    ).first()
    session.commit()
    return taken is not None


def give_back_lease(*, session: Session, holder: str) -> None:
    session.execute(
        update(CallPullLease)
        .where(col(CallPullLease.id) == 1, col(CallPullLease.holder) == holder)
        .values(held_until=datetime.now(UTC) - timedelta(seconds=1))
    )
    session.commit()


# ── Accounts ───────────────────────────────────────────────────────────────


class _Account:
    def __init__(self, fingerprint: str, api_key: str, agents: list[Agent]) -> None:
        self.fingerprint = fingerprint
        self.api_key = api_key
        self.agents = agents

    def copies(self, platform_agent_id: str) -> list[Agent]:
        return [a for a in self.agents if a.platform_agent_id == platform_agent_id]

    @property
    def platform_agent_ids(self) -> list[str]:
        return sorted({a.platform_agent_id for a in self.agents if a.platform_agent_id})


def _accounts(session: Session) -> list[_Account]:
    """Every Retell account with added agents, one per key."""
    crud.fill_key_fingerprints(session=session)
    integrations = session.exec(
        select(Integration).where(
            Integration.provider == IntegrationProvider.RETELL,
            col(Integration.key_fingerprint).is_not(None),
        )
    ).all()
    keys: dict[str, str] = {}
    for integration in integrations:
        fingerprint = integration.key_fingerprint
        if fingerprint is not None and fingerprint not in keys:
            try:
                keys[fingerprint] = decrypt(integration.encrypted_api_key)
            except InvalidToken:
                # Stored under another encryption key: no account Connexity can reach.
                continue
    accounts = []
    for fingerprint, api_key in keys.items():
        agents = crud.retell_agents_for_account(
            session=session, fingerprint=fingerprint
        )
        if agents:
            accounts.append(_Account(fingerprint, api_key, agents))
    return accounts


def _state(session: Session, fingerprint: str, now: datetime) -> CallPullAccount:
    state = session.get(CallPullAccount, fingerprint)
    if state is None:
        # Earlier calls are the first scan's.
        state = CallPullAccount(key_fingerprint=fingerprint, cursor=now)
        session.add(state)
        session.commit()
        session.refresh(state)
    return state


def _newest_call(session: Session, agents: list[Agent]) -> datetime | None:
    newest = session.exec(
        select(func.max(Call.started_at)).where(
            col(Call.agent_id).in_([a.id for a in agents]),
            col(Call.deleted_at).is_(None),
        )
    ).one()
    # Call times are stored naive, in UTC.
    return _aware(newest) if newest is not None else None


def _skip_reason(
    session: Session, account: _Account, state: CallPullAccount, now: datetime
) -> str | None:
    if state.paused_until is not None and _aware(state.paused_until) > now:
        return "paused"
    newest = _newest_call(session, account.agents)
    idle = newest is None or newest < now - IDLE_AFTER
    if (
        idle
        and state.last_pulled_at is not None
        and _aware(state.last_pulled_at) > now - IDLE_EVERY
    ):
        return "idle"
    return None


def _pause(
    session: Session, state: CallPullAccount, now: datetime, error: Exception
) -> None:
    state.failures += 1
    wait = BACKOFF_START * (2 ** (state.failures - 1))
    if isinstance(error, RetellRateLimited) and error.retry_after:
        wait = max(wait, timedelta(seconds=error.retry_after))
    wait = min(wait, BACKOFF_MAX)
    # Jitter, so accounts paused together do not come back together.
    wait += timedelta(seconds=random.uniform(0, 15))
    state.paused_until = now + wait
    detail = error.detail if isinstance(error, HTTPException) else type(error).__name__
    state.last_error = str(detail)[:255]
    session.add(state)
    session.commit()


# ── New calls ──────────────────────────────────────────────────────────────


def _stored_ids(
    session: Session, agents: list[Agent], call_ids: list[str]
) -> set[tuple[str, uuid.UUID]]:
    rows = session.exec(
        select(Call.external_id, Call.agent_id).where(
            col(Call.agent_id).in_([a.id for a in agents]),
            col(Call.external_id).in_(call_ids),
        )
    ).all()
    return {(external_id, agent_id) for external_id, agent_id in rows}  # noqa: C416


async def _pull_account(
    session: Session,
    account: _Account,
    state: CallPullAccount,
    budget: _Budget,
    now: datetime,
) -> int:
    """New calls of one account. Returns how many were stored.

    Raises:
        HTTPException: when Retell cannot be reached or rate limits; the position
            keeps what was dealt with.
    """
    page = await list_retell_call_summaries(
        account.api_key,
        agent_ids=account.platform_agent_ids,
        # From the position's own millisecond: calls that started together are not
        # skipped, and those already stored are recognised.
        after=_aware(state.cursor) - timedelta(milliseconds=1),
        until=now,
        limit=LIST_LIMIT,
    )
    stored = _stored_ids(session, account.agents, [c.call_id for c in page])
    created = 0
    # The position stops just before the first call still in progress, so it is
    # listed again; finished calls after it are stored now, and skipped when listed
    # again.
    held = False
    for summary in page:
        if (
            summary.in_progress
            and _from_ms(summary.start_timestamp) > now - STUCK_AFTER
        ):
            held = True
            continue
        missing = [
            agent
            for agent in account.copies(summary.agent_id)
            if (summary.call_id, agent.id) not in stored
        ]
        if summary.finished and missing:
            if not budget.can_read():
                break
            budget.reads += 1
            try:
                call = await get_retell_call(account.api_key, summary.call_id)
            except RetellRateLimited:
                raise
            except HTTPException:
                if state.failures < POISON_AFTER:
                    raise
                # It has failed on this call run after run: pass it over, so one call
                # cannot stop the account's other calls for good.
                logger.warning(
                    "Call pull passed over a call Retell keeps failing to return"
                )
                call = None
            if call is not None:
                for agent in missing:
                    new, _failed = await store_retell_calls(
                        session=session,
                        agent=agent,
                        api_key=account.api_key,
                        calls=[call],
                    )
                    created += new
                _no_reread_needed(session, missing, summary.call_id, now)
        if not held:
            _advance(session, state, summary)
    return created


def _no_reread_needed(
    session: Session, agents: list[Agent], call_id: str, now: datetime
) -> None:
    """A call read well after it ended already has whatever analysis it will get."""
    session.execute(
        update(Call)
        .where(
            col(Call.agent_id).in_([a.id for a in agents]),
            col(Call.external_id) == call_id,
            col(Call.ended_at) <= (now - REREAD_AFTER).replace(tzinfo=None),
        )
        .values(reread_at=now)
    )
    session.commit()


def _advance(
    session: Session, state: CallPullAccount, summary: RetellCallSummary
) -> None:
    moved = _from_ms(summary.start_timestamp)
    if moved > _aware(state.cursor):
        state.cursor = moved
        session.add(state)
        session.commit()


# ── Late analysis ──────────────────────────────────────────────────────────


async def _reread(
    session: Session, accounts: list[_Account], budget: _Budget, now: datetime
) -> int:
    """Read once more the calls stored without Retell's post-call analysis."""
    by_agent = {agent.id: account for account in accounts for agent in account.agents}
    if not by_agent:
        return 0
    calls = session.exec(
        select(Call)
        .where(
            col(Call.agent_id).in_(list(by_agent)),
            col(Call.deleted_at).is_(None),
            col(Call.reread_at).is_(None),
            col(Call.outputs).is_(None),
            col(Call.ended_at).is_not(None),
            col(Call.ended_at) <= (now - REREAD_AFTER).replace(tzinfo=None),
            col(Call.ended_at) >= (now - REREAD_WITHIN).replace(tzinfo=None),
        )
        .order_by(col(Call.ended_at))
        .limit(MAX_READS)
    ).all()
    reread = 0
    for stored in calls:
        account = by_agent[stored.agent_id]
        state = session.get(CallPullAccount, account.fingerprint)
        if (
            state is not None
            and state.paused_until
            and _aware(state.paused_until) > now
        ):
            continue
        if not budget.can_read():
            break
        budget.reads += 1
        try:
            fresh = await get_retell_call(account.api_key, stored.external_id)
            if fresh is not None and fresh.raw and fresh.raw.get("call_analysis"):
                agent = next(a for a in account.agents if a.id == stored.agent_id)
                await store_retell_calls(
                    session=session, agent=agent, api_key=account.api_key, calls=[fresh]
                )
                reread += 1
        except HTTPException as error:
            if state is not None:
                _pause(session, state, now, error)
            continue
        except Exception as error:  # noqa: BLE001 - one call must not stop the run
            logger.exception("Call pull could not read a call again")
            session.rollback()
            if state is not None:
                _pause(session, state, now, error)
            continue
        stored.reread_at = now
        session.add(stored)
        session.commit()
    return reread


# ── A run ──────────────────────────────────────────────────────────────────


async def run_pull(*, session: Session) -> PullRun:
    """One run of the scheduled pull. Never raises for a provider failure."""
    now = datetime.now(UTC)
    holder = uuid.uuid4().hex
    if not take_lease(session=session, holder=holder, now=now):
        return PullRun(status="already_running")
    run = PullRun(status="ok")
    budget = _Budget()
    started = time.monotonic()
    try:
        accounts = _accounts(session)
        states = {a.fingerprint: _state(session, a.fingerprint, now) for a in accounts}
        accounts.sort(
            key=lambda a: _aware(states[a.fingerprint].last_pulled_at)
            if states[a.fingerprint].last_pulled_at
            else datetime.min.replace(tzinfo=UTC)
        )
        for account in accounts:
            state = states[account.fingerprint]
            reason = _skip_reason(session, account, state, now)
            if reason is None and not budget.can_read():
                reason = "run_full"
            if reason is not None:
                run.skipped[reason] = run.skipped.get(reason, 0) + 1
                continue
            try:
                run.calls_stored += await _pull_account(
                    session, account, state, budget, now
                )
            except HTTPException as error:
                kind = (
                    "rate_limited" if isinstance(error, RetellRateLimited) else "failed"
                )
                run.skipped[kind] = run.skipped.get(kind, 0) + 1
                _pause(session, state, now, error)
                continue
            except Exception as error:  # noqa: BLE001 - one account must not stop the run
                logger.exception("Call pull failed for an account")
                session.rollback()
                run.skipped["error"] = run.skipped.get("error", 0) + 1
                _pause(session, state, now, error)
                continue
            state.failures = 0
            state.paused_until = None
            state.last_error = None
            state.last_pulled_at = now
            session.add(state)
            session.commit()
            run.accounts_pulled += 1
        run.calls_reread = await _reread(session, accounts, budget, now)
        run.reads = budget.reads
        return run
    finally:
        give_back_lease(session=session, holder=holder)
        emit(
            "call_pull",
            status=run.status,
            accounts_pulled=run.accounts_pulled,
            calls_stored=run.calls_stored,
            calls_reread=run.calls_reread,
            reads=budget.reads,
            skipped=run.skipped,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
