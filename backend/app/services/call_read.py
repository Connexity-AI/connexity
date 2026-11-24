"""Many calls at once for an assistant: what was said and which tools were called.

`read_calls` answers a page of calls in full, so an assistant can measure a pattern
across a period in a few requests and do its own analysis (Decided by Dmytro,
2026-11-20: Connexity filters only on what it owns; custom searches are the assistant's).

Each call is built by the same code as the single call (`call_screen`), so secrets in
tool arguments and results are masked the same way, and then cut down to what an
analysis needs: no timings, no recording, no raw payload.

A page is sized to fit an assistant's app, which caps a tool's answer in tokens. It
stops at `MAX_CALLS` or at `MAX_BYTES` of JSON, whichever comes first; a call larger
than the limit is answered alone, whole. Bytes, not characters: a character of Chinese
or Cyrillic costs an assistant several times what an English letter does, and takes
several bytes, so a page in any language stays under the cap.
"""

import uuid

from sqlmodel import Session

from app import crud
from app.crud.call_list import CallFilters
from app.models.call_screen import CallScreenEntry, KeyValue
from app.models.mcp import McpReadCall, McpReadCalls, McpReadTurn
from app.services.call_list import _item
from app.services.call_screen import call_screen

MAX_CALLS = 50
# About 15,000 tokens of English, and no more than about 20,000 in any script: under
# the 25,000 many assistant apps allow one answer.
MAX_BYTES = 60_000


def _map(pairs: list[KeyValue]) -> dict[str, str] | None:
    return {pair.key: pair.value for pair in pairs} or None


def _turn(entry: CallScreenEntry) -> McpReadTurn:
    if entry.kind == "tool":
        return McpReadTurn(
            tool=entry.tool,
            status=entry.status,
            arguments=_map(entry.arguments),
            result=_map(entry.result),
        )
    return McpReadTurn(speaker=entry.speaker, text=entry.text)


def read_calls(
    *,
    session: Session,
    company_id: uuid.UUID,
    filters: CallFilters,
    offset: int,
    limit: int,
) -> tuple[McpReadCalls, int | None]:
    """A page of calls in full, newest first, and where the next page starts (None
    when this was the last)."""
    rows, more = crud.list_workspace_calls(
        session=session,
        company_id=company_id,
        filters=filters,
        offset=offset,
        limit=min(limit, MAX_CALLS),
    )
    calls: list[McpReadCall] = []
    size = 0
    for row in rows:
        listed = _item(row)
        screen = call_screen(session=session, call=row.call)
        call = McpReadCall(
            id=listed.id,
            agent_id=listed.agent_id,
            agent_name=listed.agent_name,
            started_at=listed.started_at,
            duration_seconds=listed.duration_seconds,
            caller_last_four=listed.caller_last_four,
            result=listed.result,
            version=listed.agent_version,
            findings=[finding.text for finding in screen.findings] if screen else [],
            conversation=[_turn(entry) for entry in screen.entries] if screen else [],
        )
        length = len(call.model_dump_json().encode())
        if calls and size + length > MAX_BYTES:
            break
        calls.append(call)
        size += length
    tiles = crud.workspace_call_tiles(
        session=session, company_id=company_id, filters=filters
    )
    stopped_early = len(calls) < len(rows)
    next_offset = offset + len(calls) if (more or stopped_early) else None
    return McpReadCalls(calls=calls, matching=tiles.calls), next_offset
