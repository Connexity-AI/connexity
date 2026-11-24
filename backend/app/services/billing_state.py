"""What an agency has left and what it may do.

Each period of a subscription includes $299 of usage; usage beyond it draws from a
prepaid balance, which never goes below zero. From those and the subscription's state
comes the agency's state, and from the state whether new calls are recorded, the first
scan may read, and tests may start (`docs-internal/billing.md`).

Usage is charged in the period Connexity recorded it (`usage_record.created_at`), not
when the call happened. So an agency's first scan, recorded before it has a
subscription, is never charged, and a later scan of older calls is.

On a deployment where paying is not set up nothing here applies: `state_of` answers
None, and everything runs.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Date, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col

from app.core.config import settings
from app.crud.agency import agency_workspaces
from app.models.agency import Agency, SubscriptionState
from app.models.agent import Agent
from app.models.billing import (
    RUNNING,
    SCANNING,
    SUBSCRIPTION_INCLUDED_USD,
    AgencyState,
    BalanceEntry,
    BalanceKind,
    BillingPause,
    FirstScanPublic,
    MoneyPublic,
)
from app.models.company import Company
from app.models.enums import Platform
from app.models.usage import UsageRecord
from app.services.usage import PRICES

INCLUDED = Decimal(SUBSCRIPTION_INCLUDED_USD)
ZERO = Decimal("0.00")
CENT = Decimal("0.01")
# "Low" is less than this many days left at the rate of the last `RATE_DAYS` days,
# told only from usage on at least `RATE_MIN_DAYS` of them.
LOW_DAYS = 7
RATE_DAYS = 7
RATE_MIN_DAYS = 3

_PAID_FOR = (SubscriptionState.active, SubscriptionState.past_due)

# What an assistant tells its person when a tool is refused because of a pause.
PAUSED_NEXT_STEP = (
    "Tell the person Connexity is paused for their agency: new calls are not recorded "
    "or checked and tests cannot run. Call `get_usage` to say why. An Admin resumes "
    "it in Agency settings, Billing; you cannot."
)


@dataclass(frozen=True)
class Money:
    state: AgencyState
    included_left: Decimal
    balance: Decimal
    period_end: datetime | None
    days_left: int | None


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _company_ids(session: Session, agency_id: uuid.UUID) -> list[uuid.UUID]:
    """Every workspace of the agency, deleted ones too: their usage was real."""
    return list(
        session.execute(
            select(Company.id).where(col(Company.agency_id) == agency_id)
        ).scalars()
    )


def usage_usd(
    *, session: Session, agency_id: uuid.UUID, start: datetime, end: datetime
) -> Decimal:
    """The agency's usage recorded in a stretch of time, at list price."""
    companies = _company_ids(session, agency_id)
    if not companies:
        return ZERO
    rows = session.execute(
        select(UsageRecord.meter, func.coalesce(func.sum(UsageRecord.quantity), 0))
        .where(
            col(UsageRecord.company_id).in_(companies),
            col(UsageRecord.created_at) >= start,
            col(UsageRecord.created_at) < end,
        )
        .group_by(col(UsageRecord.meter))
    ).all()
    total = sum((PRICES[meter] * int(quantity) for meter, quantity in rows), ZERO)
    return total.quantize(CENT)


def _entries_sum(
    session: Session, agency_id: uuid.UUID, *, without_period: datetime | None
) -> Decimal:
    query = select(func.coalesce(func.sum(BalanceEntry.amount_usd), 0)).where(
        col(BalanceEntry.agency_id) == agency_id
    )
    if without_period is not None:
        query = query.where(
            ~(
                (col(BalanceEntry.kind) == BalanceKind.usage)
                & (col(BalanceEntry.period_start) == without_period)
            )
        )
    return Decimal(session.execute(query).scalar_one()).quantize(CENT)


def add_balance(
    *,
    session: Session,
    agency: Agency,
    amount_usd: Decimal,
    note: str | None,
    created_by: uuid.UUID | None,
) -> BalanceEntry:
    """Add to an agency's balance by hand. Commits."""
    entry = BalanceEntry(
        agency_id=agency.id,
        kind=BalanceKind.added,
        amount_usd=amount_usd.quantize(CENT),
        note=note,
        created_by=created_by,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def settle_period(*, session: Session, agency: Agency) -> tuple[Decimal, Decimal]:
    """Make the ledger's line for the current period say what its usage has drawn from
    the balance so far. Returns what is left of the included amount and of the balance.

    The line is rewritten, never added to, so settling twice changes nothing. The
    balance cannot go below zero: usage beyond the money left is not charged. Commits
    when the line changed.
    """
    start, end = agency.subscription_period_start, agency.subscription_period_end
    if agency.subscription_state not in _PAID_FOR or start is None or end is None:
        # No period is running: nothing is included and nothing draws.
        return ZERO, max(_entries_sum(session, agency.id, without_period=None), ZERO)
    used = usage_usd(session=session, agency_id=agency.id, start=start, end=end)
    before = max(_entries_sum(session, agency.id, without_period=start), ZERO)
    draw = min(max(used - INCLUDED, ZERO), before)
    line = session.execute(
        select(BalanceEntry).where(
            col(BalanceEntry.agency_id) == agency.id,
            col(BalanceEntry.kind) == BalanceKind.usage,
            col(BalanceEntry.period_start) == start,
        )
    ).scalar_one_or_none()
    if draw == ZERO:
        if line is not None:
            session.delete(line)
            session.commit()
    elif line is None:
        session.add(
            BalanceEntry(
                agency_id=agency.id,
                kind=BalanceKind.usage,
                amount_usd=-draw,
                period_start=start,
                note="Usage beyond the included amount",
            )
        )
        try:
            session.commit()
        except IntegrityError:
            # Another request wrote the period's line a moment earlier; it settles
            # to the same figure the next time.
            session.rollback()
    elif line.amount_usd != -draw:
        line.amount_usd = -draw
        session.add(line)
        session.commit()
    return max(INCLUDED - used, ZERO), before - draw


def _first_scan_done(session: Session, agency_id: uuid.UUID) -> bool:
    """Whether the agency has nothing left to scan without paying: every workspace
    with added voice platform agents finished its first scan. An agency whose agents
    are all its own (it sends their traces itself) has no first scan to wait for.
    False while it has no agent at all: there is nothing to pause yet."""
    workspaces = agency_workspaces(session=session, agency_id=agency_id)
    with_agents = set(
        session.execute(
            select(Agent.company_id)
            .where(
                col(Agent.company_id).in_([w.id for w in workspaces]),
                col(Agent.platform) == Platform.RETELL,
                col(Agent.integration_id).is_not(None),
                col(Agent.platform_agent_id).is_not(None),
            )
            .distinct()
        ).scalars()
    )
    scanned = [w for w in workspaces if w.id in with_agents]
    if not scanned:
        return (
            session.execute(
                select(Agent.id)
                .where(
                    col(Agent.company_id).in_([w.id for w in workspaces]),
                    col(Agent.deleted_at).is_(None),
                )
                .limit(1)
            ).first()
            is not None
        )
    return all(w.first_scan_done_at is not None for w in scanned)


def _days_left(
    session: Session, agency: Agency, left: Decimal, now: datetime
) -> int | None:
    """About how many days `left` lasts at the rate of the last days, or None with too
    little usage to tell."""
    companies = _company_ids(session, agency.id)
    since = now - timedelta(days=RATE_DAYS)
    if not companies:
        return None
    days_with_usage = session.execute(
        select(func.count(func.distinct(cast(UsageRecord.created_at, Date)))).where(
            col(UsageRecord.company_id).in_(companies),
            col(UsageRecord.created_at) >= since,
        )
    ).scalar_one()
    if days_with_usage < RATE_MIN_DAYS:
        return None
    a_day = usage_usd(session=session, agency_id=agency.id, start=since, end=now) / (
        RATE_DAYS
    )
    if a_day <= 0:
        return None
    return int(left / a_day)


def money_of(*, session: Session, agency: Agency, now: datetime | None = None) -> Money:
    """What the agency has left and its state. Settles the current period's line."""
    now = now or datetime.now(UTC)
    included_left, balance = settle_period(session=session, agency=agency)
    end = agency.subscription_period_end
    days = None
    if agency.subscription_state is SubscriptionState.unpaid:
        state = AgencyState.unpaid
    elif agency.subscription_state not in _PAID_FOR:
        state = (
            AgencyState.needs_subscription
            if _first_scan_done(session, agency.id)
            else AgencyState.first_scan
        )
    elif included_left + balance <= ZERO:
        state = AgencyState.out
    else:
        state = AgencyState.active
        days = _days_left(session, agency, included_left + balance, now)
        # Running out matters only when it comes before the next period restores the
        # included amount.
        until_period = (_aware(end) - now).days if end is not None else None
        if (
            days is not None
            and days < LOW_DAYS
            and (until_period is None or days < until_period)
        ):
            state = AgencyState.low
    return Money(
        state=state,
        included_left=included_left,
        balance=balance,
        period_end=end if agency.subscription_state in _PAID_FOR else None,
        days_left=days,
    )


def _note_pause(session: Session, agency_id: uuid.UUID, state: AgencyState) -> None:
    """Keep the record of pauses: open one when the agency stops, close it when it
    runs again. A change of reason closes one and opens another. Two requests at the
    same moment may each have opened one; every open record but the one that still
    holds is closed."""
    paused = state not in SCANNING
    open_ones = list(
        session.execute(
            select(BillingPause)
            .where(
                col(BillingPause.agency_id) == agency_id,
                col(BillingPause.ended_at).is_(None),
            )
            .order_by(col(BillingPause.started_at), col(BillingPause.id))
        ).scalars()
    )
    holds = next((p for p in open_ones if paused and p.reason is state), None)
    stale = [p for p in open_ones if p is not holds]
    if not stale and (holds is not None or not paused):
        return
    now = datetime.now(UTC)
    for pause in stale:
        pause.ended_at = now
        session.add(pause)
    if paused and holds is None:
        session.add(BillingPause(agency_id=agency_id, reason=state))
    session.commit()


def state_of(*, session: Session, agency_id: uuid.UUID) -> Money | None:
    """The agency's money and state, or None where paying is not set up. Also keeps
    the ledger's current line and the record of pauses up to date."""
    if not settings.billing_enabled:
        return None
    agency = session.get(Agency, agency_id)
    if agency is None:
        return None
    money = money_of(session=session, agency=agency)
    _note_pause(session, agency.id, money.state)
    return money


def state_for_company(*, session: Session, company_id: uuid.UUID) -> Money | None:
    company = session.get(Company, company_id)
    if company is None:
        return None
    return state_of(session=session, agency_id=company.agency_id)


def records_calls(*, session: Session, company_id: uuid.UUID) -> bool:
    """Whether a new call for this workspace is recorded and checked, and a test may
    start. Always, where paying is not set up."""
    money = state_for_company(session=session, company_id=company_id)
    return money is None or money.state in RUNNING


def may_scan(*, session: Session, company_id: uuid.UUID) -> bool:
    money = state_for_company(session=session, company_id=company_id)
    return money is None or money.state in SCANNING


def scan_is_limited(*, session: Session, company_id: uuid.UUID) -> bool:
    """Whether a scan in this workspace is the included first scan, with its limit."""
    money = state_for_company(session=session, company_id=company_id)
    return money is not None and money.state is AgencyState.first_scan


def first_scan_summary(*, session: Session, agency_id: uuid.UUID) -> FirstScanPublic:
    """How many calls the agency's included first scan read, and how many the last 30
    days held."""
    companies = [w.id for w in agency_workspaces(session=session, agency_id=agency_id)]
    if not companies:
        return FirstScanPublic(checked=0, of=0)
    checked, of = session.execute(
        select(
            func.coalesce(func.sum(Agent.scan_total), 0),
            func.coalesce(
                func.sum(func.coalesce(Agent.scan_window_total, Agent.scan_total)), 0
            ),
        ).where(col(Agent.company_id).in_(companies))
    ).one()
    return FirstScanPublic(checked=int(checked), of=int(of))


def _ended(session: Session, agency_id: uuid.UUID) -> bool:
    agency = session.get(Agency, agency_id)
    return agency is not None and agency.subscription_state is SubscriptionState.ended


def money_public(*, session: Session, agency_id: uuid.UUID) -> MoneyPublic | None:
    money = state_of(session=session, agency_id=agency_id)
    if money is None:
        return None
    no_subscription = money.state in (
        AgencyState.first_scan,
        AgencyState.needs_subscription,
    )
    return MoneyPublic(
        state=money.state,
        included_usd=float(INCLUDED) if money.period_end is not None else 0.0,
        included_left_usd=float(money.included_left),
        balance_usd=float(money.balance),
        period_end=money.period_end,
        days_left=money.days_left,
        subscription_ended=_ended(session, agency_id),
        first_scan=first_scan_summary(session=session, agency_id=agency_id)
        if no_subscription
        else None,
    )
