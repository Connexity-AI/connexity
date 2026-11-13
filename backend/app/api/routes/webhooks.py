"""Addresses that providers post to.

Each provider proves who it is its own way. A request that cannot be verified is
refused with one message, whatever the reason.
"""

import hashlib
import hmac
import json
import logging
import re
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from app import crud
from app.api.deps import SessionDep
from app.core.encryption import decrypt
from app.models import Integration
from app.models.enums import IntegrationProvider
from app.services.checks.engine import check_call_safely
from app.services.component_versions import add_retell_components
from app.services.executions import sync_call_executions_in_background
from app.services.mappings.retell import RetellMappingError, retell_call_to_trace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_RETELL_SIGNATURE = re.compile(r"^v=(\d+),d=([0-9a-fA-F]+)$")
_RETELL_MAX_AGE_MS = 5 * 60 * 1000
# The events that carry a finished call. `call_analyzed` arrives after `call_ended`
# for the same call and adds the analysis, so it replaces the first trace.
_RETELL_CALL_EVENTS = {"call_ended", "call_analyzed"}

_REFUSED = HTTPException(status_code=401, detail="Webhook could not be verified")


class WebhookResult(BaseModel):
    status: str
    reason: str | None = None
    call_id: uuid.UUID | None = None
    call_ids: list[uuid.UUID] = []


def retell_signature_is_valid(
    *, raw_body: bytes, signature: str | None, api_key: str, now_ms: int
) -> bool:
    """Retell signs ``raw body + timestamp`` with HMAC-SHA256, keyed by the API key."""
    if not signature:
        return False
    match = _RETELL_SIGNATURE.match(signature.strip())
    if match is None:
        return False
    timestamp, digest = match.group(1), match.group(2)
    if abs(now_ms - int(timestamp)) > _RETELL_MAX_AGE_MS:
        return False
    expected = hmac.new(
        api_key.encode(), raw_body + timestamp.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, digest.lower())


@router.post("/retell/{integration_id}", response_model=WebhookResult)
async def retell_webhook(
    session: SessionDep,
    request: Request,
    background_tasks: BackgroundTasks,
    integration_id: uuid.UUID,
) -> WebhookResult:
    """Receive a Retell webhook for one connected Retell account.

    Verified with the account's API key. Finished calls are converted and stored;
    everything else is acknowledged so Retell does not retry.
    """
    raw_body = await request.body()
    integration = session.get(Integration, integration_id)
    if integration is None or integration.provider != IntegrationProvider.RETELL:
        raise _REFUSED
    api_key = decrypt(integration.encrypted_api_key)
    if not retell_signature_is_valid(
        raw_body=raw_body,
        signature=request.headers.get("x-retell-signature"),
        api_key=api_key,
        now_ms=int(time.time() * 1000),
    ):
        raise _REFUSED

    try:
        body = json.loads(raw_body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Body is not JSON") from exc
    event = body.get("event") if isinstance(body, dict) else None
    payload = body.get("call") if isinstance(body, dict) else None
    if event not in _RETELL_CALL_EVENTS or not isinstance(payload, dict):
        return WebhookResult(status="ignored", reason="event not handled")

    platform_agent_id = str(payload.get("agent_id") or "")
    if integration.key_fingerprint is None:
        crud.fill_key_fingerprints(session=session)
    agents = (
        crud.retell_agents_for_account(
            session=session,
            fingerprint=integration.key_fingerprint or "",
            platform_agent_id=platform_agent_id,
        )
        if platform_agent_id
        else []
    )
    if not agents:
        return WebhookResult(status="ignored", reason="agent not connected")

    try:
        retell_call_to_trace(payload)
    except RetellMappingError as exc:
        logger.warning("Retell webhook call could not be mapped: %s", exc)
        return WebhookResult(status="ignored", reason="call could not be mapped")

    # The same Retell agent may be added in several workspaces from one Retell
    # account, but Retell sends each call to one address: store it in every one.
    call_ids: list[uuid.UUID] = []
    for agent in agents:
        trace = await add_retell_components(
            session=session,
            agent=agent,
            api_key=api_key,
            trace=retell_call_to_trace(payload),
        )
        stored = crud.store_trace(
            session=session,
            trace=trace,
            agent_id=agent.id,
            company_id=agent.company_id,
            integration_id=agent.integration_id or integration.id,
            raw=payload,
        )
        check_call_safely(session=session, call=stored.call)
        # After the response: Retell waits only ten seconds for an answer. Both
        # events look, because the executions exist as soon as the call has ended.
        background_tasks.add_task(sync_call_executions_in_background, stored.call.id)
        call_ids.append(stored.call.id)
    return WebhookResult(status="stored", call_id=call_ids[0], call_ids=call_ids)
