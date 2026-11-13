"""The first scan: each added agent's past calls, pulled once, in steps.

The assistant drives the scan through MCP (`scan_calls`), one step per call. A step
works within a time budget and stops; nothing runs after the answer, because Cloud Run
slows work once a request has been answered. Each agent keeps its own position
(`Agent.scan_cursor`), separate from its newest stored call, so calls the webhook
stores during the scan do not hide the history.

Per agent:

1. The first step lists the window's calls from Retell, which is cheap (no
   transcripts), to know the total. The window is the last `SCAN_DAYS` days, up to the
   moment of listing; later calls are the webhook's.
2. Every step lists the next page after the agent's position, skips calls already
   stored, reads the rest in full (a few at a time), stores them through the webhook's
   path and moves the position on.
3. An empty page ends the agent's scan; one pass then resolves any versions left.

Storing is idempotent and the counts come from the database, so two steps at once for
one workspace only repeat work.
"""

import time
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app import crud
from app.core.encryption import decrypt
from app.models.agent import Agent
from app.models.call import Call
from app.models.company import Company
from app.models.enums import Platform
from app.models.mcp import McpAgentScan, McpScanProgress
from app.services.call_sync import emit, store_retell_calls
from app.services.component_versions import resolve_agent_versions
from app.services.retell import (
    RetellCall,
    list_retell_call_summaries,
    read_retell_calls,
)

SCAN_DAYS = 30
# Work in one step, below Cloud Run's request limit.
STEP_SECONDS = 40.0
# Calls listed per page when counting the window, and when reading.
COUNT_PAGE = 1000
READ_PAGE = 25


def scan_agents(*, session: Session, company_id: uuid.UUID) -> list[Agent]:
    """The workspace's added Retell agents, in the order they are scanned."""
    return [
        agent
        for agent in crud.linked_agents(session=session, company_id=company_id)
        if agent.platform == Platform.RETELL
    ]


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def progress(
    *, session: Session, company_id: uuid.UUID, stored_this_step: int = 0
) -> McpScanProgress:
    agents = scan_agents(session=session, company_id=company_id)
    return McpScanProgress(
        agents=[
            McpAgentScan(
                agent_id=agent.id,
                name=agent.name,
                stored=crud.stored_in_window(session=session, agent=agent),
                total=agent.scan_total,
                finished=agent.scan_done_at is not None,
            )
            for agent in agents
        ],
        stored_this_step=stored_this_step,
        finished=bool(agents) and all(a.scan_done_at is not None for a in agents),
        calls_without_versions=crud.calls_without_versions(
            session=session, company_id=company_id
        ),
    )


def _next_after(current: datetime, last_start_ms: int) -> datetime:
    """Where the next counting page starts: just before the last listed call, so a call
    that started in the same millisecond is not skipped (calls listed twice are told
    apart by id). If that would not move on, just after it."""
    before = datetime.fromtimestamp((last_start_ms - 1) / 1000, tz=UTC)
    if before > current:
        return before
    return datetime.fromtimestamp(last_start_ms / 1000, tz=UTC)


async def _count_window(
    *, api_key: str, agent: Agent, after: datetime, until: datetime
) -> int:
    assert agent.platform_agent_id is not None
    listed: set[str] = set()
    finished: set[str] = set()
    while True:
        page = await list_retell_call_summaries(
            api_key,
            agent_ids=[agent.platform_agent_id],
            after=after,
            until=until,
            limit=COUNT_PAGE,
        )
        fresh = [call for call in page if call.call_id not in listed]
        if not fresh:
            return len(finished)
        listed.update(call.call_id for call in fresh)
        finished.update(call.call_id for call in fresh if call.finished)
        after = _next_after(after, page[-1].start_timestamp)


async def _start(*, session: Session, agent: Agent, api_key: str) -> None:
    until = datetime.now(UTC)
    since = until - timedelta(days=SCAN_DAYS)
    agent.scan_total = await _count_window(
        api_key=api_key, agent=agent, after=since, until=until
    )
    agent.scan_from = since
    agent.scan_until = until
    agent.scan_cursor = since
    session.add(agent)
    session.commit()


async def _scan_page(*, session: Session, agent: Agent, api_key: str) -> int | None:
    """Deal with the next page of the agent's window. Returns calls stored, or None
    when the window is done.

    Raises:
        HTTPException: 502 when Retell cannot be reached (what was stored is kept).
    """
    assert agent.platform_agent_id is not None
    assert agent.scan_cursor is not None and agent.scan_until is not None
    # From just before the position, so calls that started in the same millisecond as
    # the last one dealt with are listed again; those already stored are skipped.
    page = await list_retell_call_summaries(
        api_key,
        agent_ids=[agent.platform_agent_id],
        after=_aware(agent.scan_cursor) - timedelta(milliseconds=1),
        until=_aware(agent.scan_until),
        limit=READ_PAGE,
    )
    if not page:
        return None
    cursor_ms = int(_aware(agent.scan_cursor).timestamp() * 1000)
    beyond = any(c.start_timestamp > cursor_ms for c in page)

    stored = set(
        session.exec(
            select(Call.external_id).where(
                Call.agent_id == agent.id,
                col(Call.external_id).in_([c.call_id for c in page]),
            )
        ).all()
    )
    # Calls still in progress are the webhook's; calls already stored are skipped.
    wanted = [c for c in page if c.finished and c.call_id not in stored]
    read = await read_retell_calls(api_key, [c.call_id for c in wanted])

    # Move on to just before the first call that could not be read.
    reached = len(page)
    if len(read) < len(wanted):
        missed = wanted[len(read)].call_id
        reached = next(i for i, c in enumerate(page) if c.call_id == missed)
    calls: list[RetellCall] = [c for c in read if c is not None]
    created, _failed = await store_retell_calls(
        session=session, agent=agent, api_key=api_key, calls=calls
    )
    if reached:
        moved = datetime.fromtimestamp(page[reached - 1].start_timestamp / 1000, tz=UTC)
        if moved > _aware(agent.scan_cursor):
            agent.scan_cursor = moved
            session.add(agent)
            session.commit()
    if reached < len(page):
        raise HTTPException(status_code=502, detail="Retell API failed reading a call")
    if not beyond:
        if len(page) < READ_PAGE:
            # Only the position's own millisecond is left. The window is done, unless
            # this page stored something: then the next page, with nothing new, says so.
            return created if created else None
        # A whole page of calls started in the position's millisecond: move past it.
        agent.scan_cursor = _aware(agent.scan_cursor) + timedelta(milliseconds=1)
        session.add(agent)
        session.commit()
    return created


async def scan_step(*, session: Session, company_id: uuid.UUID) -> McpScanProgress:
    """One step of the workspace's first scan, within `STEP_SECONDS`.

    Raises:
        HTTPException: 502 when Retell cannot be reached; what was stored is kept and
            the next step carries on from there.
    """
    deadline = time.monotonic() + STEP_SECONDS
    stored = 0
    worked = False
    try:
        for agent in scan_agents(session=session, company_id=company_id):
            if agent.scan_done_at is not None:
                continue
            if agent.integration_id is None:
                continue
            integration = crud.get_integration(
                session=session,
                integration_id=agent.integration_id,
                company_id=company_id,
            )
            if integration is None:
                continue
            api_key = decrypt(integration.encrypted_api_key)
            if agent.scan_until is None:
                await _start(session=session, agent=agent, api_key=api_key)
                if time.monotonic() >= deadline:
                    # Counting a large window used the step; reading starts next step.
                    worked = True
                    break
            # At least one page per step, so a step always moves the scan on.
            while not worked or time.monotonic() < deadline:
                worked = True
                created = await _scan_page(
                    session=session, agent=agent, api_key=api_key
                )
                if created is None:
                    agent.scan_done_at = datetime.now(UTC)
                    session.add(agent)
                    session.commit()
                    # Calls stored while the provider could not say which version
                    # served them.
                    await resolve_agent_versions(session=session, agent=agent)
                    break
                stored += created
            if worked and time.monotonic() >= deadline:
                break
    finally:
        emit("first_scan_step", company_id=str(company_id), stored=stored)

    result = progress(session=session, company_id=company_id, stored_this_step=stored)
    if result.finished:
        company = session.get(Company, company_id)
        if company is not None and company.first_scan_done_at is None:
            company.first_scan_done_at = datetime.now(UTC)
            session.add(company)
            session.commit()
    return result
