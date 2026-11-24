"""An agency's usage on Agency settings › Billing: what was used in a period and what
used it, per client workspace and per agent.

It counts the way the money is drawn (`services/billing_state.py`): by when Connexity
recorded the usage, in subscription periods, in every workspace of the agency, deleted
ones too. So "this period" is exactly what came off the included amount and the
balance. Dollars are units times the list price; Connexity's own model costs are never
read here.
"""

import csv
import io
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlmodel import Session, col

from app.models.agency import Agency, SubscriptionState
from app.models.agent import Agent
from app.models.billing import (
    AgencyUsagePublic,
    AgentUsagePublic,
    UsageMoverLine,
    UsagePartPublic,
    UsagePeriodPublic,
    WorkspaceUsagePublic,
)
from app.models.company import Company
from app.models.enums import UsageMeter
from app.models.usage import UsageRecord
from app.services.usage import PRICES

PeriodKey = Literal["this", "last", "30d"]
MOVERS = 3

_PARTS: dict[UsageMeter, tuple[str, str]] = {
    UsageMeter.OBSERVED_MINUTES: ("Calls observed", "min"),
    UsageMeter.SIMULATED_CALLER_MESSAGES: ("Text simulations", "messages"),
    UsageMeter.VOICE_SIMULATION_MINUTES: ("Voice simulations", "min"),
}
# Shown also when nothing was used; voice simulations only once they exist.
_ALWAYS = (UsageMeter.OBSERVED_MINUTES, UsageMeter.SIMULATED_CALLER_MESSAGES)


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _month_before(moment: datetime) -> datetime:
    """The same day and time one month earlier; the month's last day when it has no
    such day (31 March gives 28 or 29 February)."""
    year, month = (
        (moment.year, moment.month - 1)
        if moment.month > 1
        else (
            moment.year - 1,
            12,
        )
    )
    day = moment.day
    while True:
        try:
            return moment.replace(year=year, month=month, day=day)
        except ValueError:
            day -= 1


def periods(agency: Agency, now: datetime) -> list[UsagePeriodPublic]:
    """The periods on offer: the subscription's current and previous period when it
    has one, and always the last 30 days."""
    found: list[UsagePeriodPublic] = []
    start, end = agency.subscription_period_start, agency.subscription_period_end
    running = agency.subscription_state in (
        SubscriptionState.active,
        SubscriptionState.past_due,
        SubscriptionState.unpaid,
    )
    if running and start is not None and end is not None:
        start, end = _aware(start), _aware(end)
        found.append(
            UsagePeriodPublic(
                key="this", label="This period", starts_at=start, ends_at=end
            )
        )
        found.append(
            UsagePeriodPublic(
                key="last",
                label="Last period",
                starts_at=_month_before(start),
                ends_at=start,
            )
        )
    found.append(
        UsagePeriodPublic(
            key="30d",
            label="Last 30 days",
            starts_at=now - timedelta(days=30),
            ends_at=now,
        )
    )
    return found


def _dollars(quantities: dict[UsageMeter, int]) -> Decimal:
    return sum((PRICES[m] * q for m, q in quantities.items()), Decimal("0"))


def _money(amount: Decimal) -> float:
    return float(amount.quantize(Decimal("0.01")))


def agency_usage(
    *,
    session: Session,
    agency: Agency,
    period: PeriodKey | None,
    now: datetime | None = None,
) -> AgencyUsagePublic:
    """The agency's usage in one period. An unknown or unavailable period falls back
    to the first on offer: this period with a subscription, the last 30 days without."""
    now = now or datetime.now(UTC)
    on_offer = periods(agency, now)
    chosen = next((p for p in on_offer if p.key == period), on_offer[0])
    workspaces = {
        company.id: company
        for company in session.execute(
            select(Company).where(col(Company.agency_id) == agency.id)
        ).scalars()
    }
    in_period = (
        col(UsageRecord.company_id).in_(list(workspaces)),
        col(UsageRecord.created_at) >= chosen.starts_at,
        col(UsageRecord.created_at) < chosen.ends_at,
    )
    rows = (
        session.execute(
            select(
                UsageRecord.company_id,
                UsageRecord.agent_id,
                UsageRecord.meter,
                func.coalesce(func.sum(UsageRecord.quantity), 0),
            )
            .where(*in_period)
            .group_by(
                col(UsageRecord.company_id),
                col(UsageRecord.agent_id),
                col(UsageRecord.meter),
            )
        ).all()
        if workspaces
        else []
    )
    by_agent: dict[tuple[uuid.UUID, uuid.UUID], dict[UsageMeter, int]] = defaultdict(
        dict
    )
    totals: dict[UsageMeter, int] = defaultdict(int)
    for company_id, agent_id, meter, quantity in rows:
        by_agent[(company_id, agent_id)][meter] = int(quantity)
        totals[meter] += int(quantity)
    names = (
        dict(
            session.execute(
                select(Agent.id, Agent.name).where(
                    col(Agent.id).in_([agent_id for _, agent_id in by_agent])
                )
            ).all()
        )
        if by_agent
        else {}
    )

    listed: list[WorkspaceUsagePublic] = []
    for company_id, company in workspaces.items():
        agents = [
            AgentUsagePublic(
                id=agent_id,
                name=names.get(agent_id, "Deleted agent"),
                observed_minutes=used.get(UsageMeter.OBSERVED_MINUTES, 0),
                simulated_messages=used.get(UsageMeter.SIMULATED_CALLER_MESSAGES, 0),
                cost_usd=_money(_dollars(used)),
            )
            for (owner, agent_id), used in by_agent.items()
            if owner == company_id
        ]
        if not agents:
            continue
        agents.sort(key=lambda a: (-a.cost_usd, a.name.lower()))
        used_here: dict[UsageMeter, int] = defaultdict(int)
        for (owner, _), used in by_agent.items():
            if owner == company_id:
                for meter, quantity in used.items():
                    used_here[meter] += quantity
        listed.append(
            WorkspaceUsagePublic(
                id=company_id,
                name=company.name,
                deleted=company.deleted_at is not None,
                observed_minutes=used_here.get(UsageMeter.OBSERVED_MINUTES, 0),
                simulated_messages=used_here.get(
                    UsageMeter.SIMULATED_CALLER_MESSAGES, 0
                ),
                cost_usd=_money(_dollars(used_here)),
                agents=agents,
            )
        )
    listed.sort(key=lambda w: (-w.cost_usd, w.name.lower()))

    parts = [
        UsagePartPublic(
            meter=meter.value,
            label=_PARTS[meter][0],
            quantity=totals.get(meter, 0),
            unit=_PARTS[meter][1],
            unit_price_usd=float(PRICES[meter]),
            cost_usd=_money(PRICES[meter] * totals.get(meter, 0)),
        )
        for meter in _PARTS
        if meter in _ALWAYS or totals.get(meter, 0)
    ]
    return AgencyUsagePublic(
        period=chosen,
        periods=on_offer,
        cost_usd=_money(_dollars(totals)),
        parts=parts,
        workspaces=listed,
        movers=_movers(session, listed, names, in_period),
    )


def _movers(
    session: Session,
    workspaces: list[WorkspaceUsagePublic],
    agent_names: dict[uuid.UUID, str],
    in_period: tuple[object, ...],
) -> list[UsageMoverLine]:
    """The things that added most: a test run's simulated messages, or a workspace's
    observed calls."""
    found = [
        UsageMoverLine(
            label=f"{w.name}’s calls",
            quantity=w.observed_minutes,
            unit="min",
            cost_usd=_money(PRICES[UsageMeter.OBSERVED_MINUTES] * w.observed_minutes),
        )
        for w in workspaces
        if w.observed_minutes
    ]
    if workspaces:
        runs = session.execute(
            select(
                UsageRecord.run_id,
                UsageRecord.agent_id,
                func.sum(UsageRecord.quantity),
                func.min(UsageRecord.created_at),
            )
            .where(
                *in_period,  # type: ignore[arg-type]
                col(UsageRecord.meter) == UsageMeter.SIMULATED_CALLER_MESSAGES,
                col(UsageRecord.run_id).is_not(None),
            )
            .group_by(col(UsageRecord.run_id), col(UsageRecord.agent_id))
        ).all()
        for _run_id, agent_id, quantity, first in runs:
            on = _aware(first)
            found.append(
                UsageMoverLine(
                    label=f"Test run on {agent_names.get(agent_id, 'a deleted agent')}, "
                    f"{on.day} {on:%b}",
                    quantity=int(quantity),
                    unit="messages",
                    cost_usd=_money(
                        PRICES[UsageMeter.SIMULATED_CALLER_MESSAGES] * int(quantity)
                    ),
                )
            )
    found.sort(key=lambda m: (-m.cost_usd, m.label))
    return [m for m in found if m.cost_usd > 0][:MOVERS]


def as_csv(usage: AgencyUsagePublic) -> str:
    """One row per workspace and agent, then a total, for billing each client."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "Workspace",
            "Agent",
            "Calls observed (min)",
            "Simulated messages",
            "Cost (USD)",
        ]
    )
    for workspace in usage.workspaces:
        for agent in workspace.agents:
            writer.writerow(
                [
                    _safe(workspace.name),
                    _safe(agent.name),
                    agent.observed_minutes,
                    agent.simulated_messages,
                    f"{agent.cost_usd:.2f}",
                ]
            )
    writer.writerow(
        [
            "Total",
            "",
            sum(w.observed_minutes for w in usage.workspaces),
            sum(w.simulated_messages for w in usage.workspaces),
            f"{usage.cost_usd:.2f}",
        ]
    )
    return out.getvalue()


def _safe(text: str) -> str:
    """A name a spreadsheet will not run as a formula."""
    return f"'{text}" if text[:1] in ("=", "+", "-", "@") else text
