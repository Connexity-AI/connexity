"""Pull an agent's calls from its provider.

Works from the agent's own link to its provider account (``integration_id``) and
provider agent (``platform_agent_id``). Retell calls are converted to traces. Vapi and
ElevenLabs calls are stored with their original payload only, until they are mapped.
"""

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session

from app import crud
from app.core.encryption import decrypt
from app.models.agent import Agent
from app.models.enums import Platform
from app.services.checks.engine import check_call_safely
from app.services.component_versions import add_retell_components
from app.services.elevenlabs import (
    get_elevenlabs_conversation,
    list_elevenlabs_conversations,
)
from app.services.executions import sync_call_executions_safely
from app.services.mappings.retell import RetellMappingError, retell_call_to_trace
from app.services.retell import RetellCall, list_retell_calls
from app.services.vapi import list_vapi_calls

logger = logging.getLogger(__name__)

PAGE_SIZE = 100
MAX_FETCH_ITERATIONS = 20

_SYNCABLE = {Platform.RETELL, Platform.VAPI, Platform.ELEVENLABS}


def emit(event: str, **fields: Any) -> None:
    """Emit one wide-event log line as JSON. Never put call content in ``fields``."""
    logger.warning(json.dumps({"event": event, **fields}, default=str))


async def store_retell_calls(
    *, session: Session, agent: Agent, api_key: str, calls: list[RetellCall]
) -> tuple[int, int]:
    """Convert and store Retell calls, then look for each new call's executions.

    Returns ``(created, failed)``.
    """
    created = 0
    failed = 0
    has_backends = bool(crud.list_tool_backends(session=session, agent_id=agent.id))
    for call in calls:
        if call.raw is None:
            failed += 1
            continue
        try:
            trace = retell_call_to_trace(call.raw)
        except RetellMappingError as exc:
            failed += 1
            logger.warning("Retell call %s could not be mapped: %s", call.call_id, exc)
            continue
        trace = await add_retell_components(
            session=session, agent=agent, api_key=api_key, trace=trace
        )
        stored = crud.store_trace(
            session=session,
            trace=trace,
            agent_id=agent.id,
            company_id=agent.company_id,
            integration_id=agent.integration_id,
            raw=call.raw,
        )
        created += stored.created
        check_call_safely(session=session, call=stored.call)
        # Only for a call seen for the first time: a backend keeps its history for a
        # while only, and an old call can be looked up again on request.
        if stored.created and has_backends:
            await sync_call_executions_safely(session=session, call=stored.call)
    return created, failed


async def sync_agent_calls(*, session: Session, agent: Agent, incremental: bool) -> int:
    """Pull new calls for ``agent`` from its provider. Returns how many were new.

    Raises:
        HTTPException: 400 when the agent is not linked to a provider account;
            502 when the provider cannot be reached.
    """
    started = time.monotonic()
    event: dict[str, Any] = {
        "agent_id": str(agent.id),
        "platform": agent.platform,
        "incremental": incremental,
        "iterations": 0,
        "fetched": 0,
        "created": 0,
        "failed": 0,
        "status": "ok",
    }
    try:
        if (
            agent.platform not in _SYNCABLE
            or agent.integration_id is None
            or not agent.platform_agent_id
        ):
            event["status"] = "not_linked"
            raise HTTPException(
                status_code=400,
                detail="This agent is not linked to a provider account",
            )
        integration = crud.get_integration(
            session=session,
            integration_id=agent.integration_id,
            company_id=agent.company_id,
        )
        if integration is None:
            event["status"] = "missing_integration"
            raise HTTPException(
                status_code=400,
                detail="This agent's provider account is no longer connected",
            )
        api_key = decrypt(integration.encrypted_api_key)

        start_after: datetime | None = None
        if incremental:
            latest = crud.get_latest_call_started_at(
                session=session,
                agent_id=agent.id,
                provider_agent_id=agent.platform_agent_id,
            )
            # Call timestamps are stored naive, in UTC.
            start_after = latest.replace(tzinfo=UTC) if latest else None
        event["start_after"] = start_after

        for iteration in range(MAX_FETCH_ITERATIONS):
            event["iterations"] = iteration + 1
            next_after: datetime | None
            if agent.platform == Platform.RETELL:
                batch = await list_retell_calls(
                    api_key,
                    agent_id=agent.platform_agent_id,
                    start_after=start_after,
                    limit=PAGE_SIZE,
                )
                created, failed = await store_retell_calls(
                    session=session, agent=agent, api_key=api_key, calls=batch
                )
                event["failed"] += failed
                newest = max(
                    (c.start_timestamp for c in batch if c.start_timestamp),
                    default=None,
                )
                next_after = (
                    datetime.fromtimestamp(newest / 1000, tz=UTC) if newest else None
                )
                fetched = len(batch)
            elif agent.platform == Platform.VAPI:
                vapi_batch = await list_vapi_calls(
                    api_key,
                    assistant_id=agent.platform_agent_id,
                    start_after=start_after,
                    limit=PAGE_SIZE,
                )
                created = crud.upsert_calls_from_vapi(
                    session=session,
                    agent_id=agent.id,
                    company_id=agent.company_id,
                    integration_id=integration.id,
                    vapi_calls=vapi_batch,
                )
                next_after = max(
                    (
                        started_at
                        for c in vapi_batch
                        if (started_at := c.started_at or c.created_at) is not None
                    ),
                    default=None,
                )
                fetched = len(vapi_batch)
            else:
                summaries = await list_elevenlabs_conversations(
                    api_key,
                    agent_id=agent.platform_agent_id,
                    start_after=start_after,
                    page_size=PAGE_SIZE,
                    max_pages=1,
                )
                conversations = [
                    await get_elevenlabs_conversation(
                        api_key, conversation_id=s.conversation_id
                    )
                    for s in summaries
                ]
                created = crud.upsert_calls_from_elevenlabs(
                    session=session,
                    agent_id=agent.id,
                    company_id=agent.company_id,
                    integration_id=integration.id,
                    conversations=conversations,
                )
                newest_unix = max(
                    (
                        c.start_time_unix_secs
                        for c in conversations
                        if c.start_time_unix_secs
                    ),
                    default=None,
                )
                next_after = (
                    datetime.fromtimestamp(newest_unix, tz=UTC) if newest_unix else None
                )
                fetched = len(conversations)

            if not fetched:
                break
            event["fetched"] += fetched
            event["created"] += created
            if fetched < PAGE_SIZE or next_after is None:
                break
            if start_after is not None and next_after <= start_after:
                break
            start_after = next_after
        return int(event["created"])
    except HTTPException as exc:
        if event["status"] == "ok":
            event["status"] = "http_error"
        event["error"] = f"{exc.status_code}: {exc.detail}"
        raise
    finally:
        event["duration_ms"] = int((time.monotonic() - started) * 1000)
        emit("call_sync", **event)
