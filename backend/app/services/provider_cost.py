"""Reads what Anthropic billed for the last days and stores it beside what Connexity
recorded (`provider_cost_day`). Plan: `plans/2026-11-23-anthropic-cost-comparison.md`.

Anthropic answers a request with token counts, never dollars; dollars exist only in the
organisation's cost report, some hours behind. So a day is read again until it is
`FINAL_AFTER_DAYS` old. Nothing here judges a difference: the numbers sit side by side.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import httpx
from pydantic import BaseModel, ValidationError
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, func, select

from app.core.config import settings
from app.models.provider_cost import ProviderCostDay
from app.models.usage import UsageRecord

logger = logging.getLogger(__name__)

PROVIDER = "anthropic"
API = "https://api.anthropic.com/v1/organizations"
COST_REPORT = f"{API}/cost_report"
USAGE_REPORT = f"{API}/usage_report/messages"
API_VERSION = "2023-06-01"
TIMEOUT_SECONDS = 10.0
# The whole read, both reports: it runs inside the call pull, whose caller waits a
# minute at most.
READ_SECONDS = 12.0
MAX_PAGES = 10
# A day is read again until it is this old; the reports run some hours behind.
FINAL_AFTER_DAYS = 3
# Read at most this often. Kept in this process only: another instance may read once
# more, which is harmless.
READ_EVERY = 6 * 3600.0
# After a read that failed, the next one is tried this soon.
RETRY_EVERY = 600.0
_next_read: float | None = None


class _CostLine(BaseModel):
    amount: str
    model: str | None = None


class _UsageLine(BaseModel):
    model: str | None = None
    uncached_input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation: dict[str, int] | None = None


class _Bucket[Line: BaseModel](BaseModel):
    starting_at: datetime
    results: list[Line]


class _Page[Line: BaseModel](BaseModel):
    data: list[_Bucket[Line]]
    has_more: bool = False
    next_page: str | None = None


@dataclass
class _Totals:
    usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


type _Key = tuple[date, str]


async def _pages[Line: BaseModel](
    client: httpx.AsyncClient,
    url: str,
    params: list[tuple[str, str]],
    line: type[Line],
) -> list[_Bucket[Line]]:
    buckets: list[_Bucket[Line]] = []
    page: str | None = None
    for _ in range(MAX_PAGES):
        response = await client.get(
            url, params=[*params, *([("page", page)] if page else [])]
        )
        response.raise_for_status()
        answer = _Page[line].model_validate(response.json())
        buckets += answer.data
        if not answer.has_more or not answer.next_page:
            break
        page = answer.next_page
    return buckets


async def read_billed(*, key: str, start: date, end: date) -> dict[_Key, _Totals]:
    """What Anthropic billed per day and model from ``start`` up to, not including,
    ``end``. Raises on a failed request or an answer in another shape."""
    window = [
        ("starting_at", f"{start.isoformat()}T00:00:00Z"),
        ("ending_at", f"{end.isoformat()}T00:00:00Z"),
        ("limit", "31"),
    ]
    billed: dict[_Key, _Totals] = defaultdict(_Totals)
    async with httpx.AsyncClient(
        timeout=TIMEOUT_SECONDS,
        headers={"x-api-key": key, "anthropic-version": API_VERSION},
    ) as client:
        costs = await _pages(
            client, COST_REPORT, [*window, ("group_by[]", "description")], _CostLine
        )
        used = await _pages(
            client,
            USAGE_REPORT,
            [*window, ("bucket_width", "1d"), ("group_by[]", "model")],
            _UsageLine,
        )
    for bucket in costs:
        for cost in bucket.results:
            # The report gives amounts in cents.
            billed[(bucket.starting_at.date(), cost.model or "")].usd += (
                float(cost.amount) / 100
            )
    for bucket in used:
        for use in bucket.results:
            totals = billed[(bucket.starting_at.date(), use.model or "")]
            totals.input_tokens += use.uncached_input_tokens
            totals.output_tokens += use.output_tokens
            totals.cache_read_tokens += use.cache_read_input_tokens
            totals.cache_write_tokens += sum((use.cache_creation or {}).values())
    return dict(billed)


def recorded(*, session: Session, start: date, end: date) -> dict[_Key, _Totals]:
    """What Connexity recorded for Anthropic's models per day (UTC) and model, summed
    from every workspace's usage records."""
    day = func.date(func.timezone("UTC", col(UsageRecord.occurred_at)))
    rows = session.exec(
        select(
            day,
            UsageRecord.model,
            func.sum(col(UsageRecord.own_cost_usd)),
            func.sum(col(UsageRecord.input_tokens)),
            func.sum(col(UsageRecord.output_tokens)),
            func.sum(col(UsageRecord.cache_read_tokens)),
            func.sum(col(UsageRecord.cache_write_tokens)),
        )
        .where(
            col(UsageRecord.occurred_at)
            >= datetime.combine(start, datetime.min.time(), UTC),
            col(UsageRecord.occurred_at)
            < datetime.combine(end, datetime.min.time(), UTC),
            col(UsageRecord.model).startswith("claude"),
        )
        .group_by(day, col(UsageRecord.model))
    ).all()
    return {
        (on, model): _Totals(float(usd), int(i), int(o), int(read), int(write))
        for on, model, usd, i, o, read, write in rows
    }


def store_days(
    *,
    session: Session,
    billed: dict[_Key, _Totals],
    recorded: dict[_Key, _Totals],
    now: datetime,
) -> int:
    """One row per day and model either side has numbers for. Commits."""
    keys = sorted(billed.keys() | recorded.keys())
    for on, model in keys:
        b = billed.get((on, model), _Totals())
        r = recorded.get((on, model), _Totals())
        values = {
            "billed_usd": round(b.usd, 6),
            "billed_input_tokens": b.input_tokens,
            "billed_output_tokens": b.output_tokens,
            "billed_cache_read_tokens": b.cache_read_tokens,
            "billed_cache_write_tokens": b.cache_write_tokens,
            "recorded_usd": round(r.usd, 6),
            "recorded_input_tokens": r.input_tokens,
            "recorded_output_tokens": r.output_tokens,
            "recorded_cache_read_tokens": r.cache_read_tokens,
            "recorded_cache_write_tokens": r.cache_write_tokens,
            "read_at": now,
        }
        session.execute(
            insert(ProviderCostDay)
            .values(day=on, provider=PROVIDER, model=model, **values)
            .on_conflict_do_update(
                constraint="uq_provider_cost_day_day_provider_model", set_=values
            )
        )
    session.commit()
    return len(keys)


async def read_provider_costs(
    *, session: Session, now: datetime | None = None, force: bool = False
) -> int | None:
    """Read the days not final yet and store them. Runs at most every `READ_EVERY`, or `RETRY_EVERY` after a read that failed.

    Returns the rows stored, or None when nothing was read: no admin key, not due yet,
    or Anthropic did not answer. Never raises: the caller is the scheduled call pull.
    """
    global _next_read
    key = settings.ANTHROPIC_ADMIN_KEY
    if not key:
        return None
    if not force and _next_read is not None and time.monotonic() < _next_read:
        return None
    _next_read = time.monotonic() + RETRY_EVERY
    now = now or datetime.now(UTC)
    end = now.date() + timedelta(days=1)
    start = now.date() - timedelta(days=FINAL_AFTER_DAYS)
    try:
        async with asyncio.timeout(READ_SECONDS):
            billed = await read_billed(key=key, start=start, end=end)
    except (httpx.HTTPError, ValidationError, ValueError, TimeoutError) as exc:
        # Tried again after `RETRY_EVERY`; the table stays as it was.
        status = (
            f" (HTTP {exc.response.status_code})"
            if isinstance(exc, httpx.HTTPStatusError)
            else ""
        )
        logger.warning(
            "Anthropic's cost report was not read: %s%s", type(exc).__name__, status
        )
        return None
    try:
        stored = store_days(
            session=session,
            billed=billed,
            recorded=recorded(session=session, start=start, end=end),
            now=now,
        )
        _next_read = time.monotonic() + READ_EVERY
        return stored
    except Exception:  # noqa: BLE001 - must not fail the call pull
        session.rollback()
        logger.exception("Storing the provider's cost days failed")
        return None
