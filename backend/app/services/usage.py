"""A workspace's usage at list price: what was counted, and what it would cost.

Nothing is billed. The prices are Connexity's list prices (Dmytro, roadmap row,
2026-11-20); dollars are always units times the price here, at the time of reading.
Connexity's own model cost sits on the same records and is never returned from here.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlmodel import Session, col, select

from app.crud import usage as crud_usage
from app.models import Agent, Run
from app.models.enums import UsageMeter
from app.models.usage import (
    UsageAgentPublic,
    UsageLinePublic,
    UsageMoverPublic,
    UsagePublic,
    UsageRunPublic,
)

UsagePeriod = Literal["month", "7d", "30d"]

# Dollars per unit.
PRICES: dict[UsageMeter, Decimal] = {
    UsageMeter.OBSERVED_MINUTES: Decimal("0.03"),
    UsageMeter.SIMULATED_CALLER_MESSAGES: Decimal("0.02"),
    UsageMeter.VOICE_SIMULATION_MINUTES: Decimal("0.25"),
}
UNITS: dict[UsageMeter, str] = {
    UsageMeter.OBSERVED_MINUTES: "minute of a real call, each started minute whole",
    UsageMeter.SIMULATED_CALLER_MESSAGES: "message the simulated caller sent",
    UsageMeter.VOICE_SIMULATION_MINUTES: "minute of a voice simulation",
}
MOVERS = 3


class BadMonth(ValueError):
    """`month` is not a calendar month written YYYY-MM."""


def list_price(meter: UsageMeter, quantity: int) -> float:
    return float(PRICES[meter] * quantity)


def messages_price(messages: int) -> float:
    return list_price(UsageMeter.SIMULATED_CALLER_MESSAGES, messages)


def window(
    period: UsagePeriod, month: str | None, now: datetime
) -> tuple[datetime, datetime]:
    """The period's start and (exclusive) end, in UTC."""
    if period != "month":
        return now - timedelta(days=int(period.removesuffix("d"))), now
    if month is None:
        first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            first = datetime.strptime(month, "%Y-%m").replace(tzinfo=UTC)
        except ValueError:
            raise BadMonth(month) from None
    following = (first + timedelta(days=32)).replace(day=1)
    return first, following


def _lines(quantities: dict[UsageMeter, int]) -> list[UsageLinePublic]:
    # Voice simulation minutes are in the price list and recorded by nothing yet, so
    # they show only once something records them.
    return [
        UsageLinePublic(
            meter=meter,
            unit=UNITS[meter],
            quantity=quantities.get(meter, 0),
            unit_price_usd=float(PRICES[meter]),
            cost_usd=list_price(meter, quantities.get(meter, 0)),
        )
        for meter in UsageMeter
        if meter is not UsageMeter.VOICE_SIMULATION_MINUTES or quantities.get(meter)
    ]


def _total(quantities: dict[UsageMeter, int]) -> float:
    return float(sum(PRICES[meter] * n for meter, n in quantities.items()))


def usage(
    *,
    session: Session,
    company_id: uuid.UUID,
    period: UsagePeriod = "month",
    month: str | None = None,
    agent_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 25,
    now: datetime | None = None,
) -> tuple[UsagePublic, bool]:
    """The workspace's usage over the period, and whether more runs follow the page."""
    starts_at, ends_at = window(period, month, now or datetime.now(UTC))
    scope = {
        "session": session,
        "company_id": company_id,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "agent_id": agent_id,
    }
    per_agent: dict[uuid.UUID, dict[UsageMeter, int]] = {}
    for agent, meter, quantity in crud_usage.usage_by_agent(**scope):
        per_agent.setdefault(agent, {})[meter] = quantity
    totals: dict[UsageMeter, int] = {}
    for quantities in per_agent.values():
        for meter, quantity in quantities.items():
            totals[meter] = totals.get(meter, 0) + quantity

    by_run = crud_usage.usage_by_run(**scope)
    days = crud_usage.observed_by_day(**scope, limit=MOVERS)
    names = dict(
        session.exec(
            select(Agent.id, Agent.name).where(
                col(Agent.id).in_(
                    {*per_agent, *(a for _, a, *_ in by_run), *(a for a, *_ in days)}
                )
            )
        ).all()
    )
    run_rows = {
        run_id: (set_name, started_at or created_at)
        for run_id, set_name, started_at, created_at in session.exec(
            select(Run.id, Run.set_name, Run.started_at, Run.created_at).where(
                col(Run.id).in_([run for run, *_ in by_run])
            )
        ).all()
    }
    runs = [
        UsageRunPublic(
            run_id=run,
            agent_id=agent,
            agent_name=names.get(agent, ""),
            set_name=run_rows[run][0] if run in run_rows else None,
            started_at=_utc(run_rows[run][1]) if run in run_rows else at,
            simulated_calls=calls,
            caller_messages=messages,
            cost_usd=messages_price(messages),
        )
        for run, agent, calls, messages, at in by_run
    ]
    movers = [
        UsageMoverPublic(
            kind="run",
            line=(
                f"Run of {_set(r.set_name)} on {_day(r.started_at)} "
                f"({r.agent_name}): {r.caller_messages} caller messages, "
                f"${r.cost_usd:.2f}"
            ),
            agent_id=r.agent_id,
            run_id=r.run_id,
            quantity=r.caller_messages,
            cost_usd=r.cost_usd,
        )
        for r in runs[:MOVERS]
    ] + [
        UsageMoverPublic(
            kind="calls",
            line=(
                f"Real calls of {names.get(agent, '')} on {_day(on)}: {minutes} "
                f"observed minutes, "
                f"${list_price(UsageMeter.OBSERVED_MINUTES, minutes):.2f}"
            ),
            agent_id=agent,
            day=on.isoformat(),
            quantity=minutes,
            cost_usd=list_price(UsageMeter.OBSERVED_MINUTES, minutes),
        )
        for agent, on, minutes in days
    ]
    movers.sort(key=lambda m: m.cost_usd, reverse=True)
    return (
        UsagePublic(
            period=period,
            starts_at=starts_at,
            ends_at=ends_at,
            agent_id=agent_id,
            lines=_lines(totals),
            cost_usd=_total(totals),
            agents=sorted(
                (
                    UsageAgentPublic(
                        agent_id=agent,
                        name=names.get(agent, ""),
                        lines=_lines(quantities),
                        cost_usd=_total(quantities),
                    )
                    for agent, quantities in per_agent.items()
                ),
                key=lambda a: a.cost_usd,
                reverse=True,
            ),
            runs=runs[offset : offset + limit],
            movers=movers[:MOVERS],
        ),
        len(runs) > offset + limit,
    )


def _set(name: str | None) -> str:
    return f"'{name}'" if name else "chosen scenarios"


def _utc(moment: datetime) -> datetime:
    # Run timestamps are stored naive, in UTC.
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment


def _day(moment: datetime | date) -> str:
    if isinstance(moment, datetime):
        moment = moment.astimezone(UTC)
    return f"{moment:%-d %b}"
