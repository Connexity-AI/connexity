"""The single call screen: what it shows, and where its recording plays from."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import crud
from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.core.encryption import decrypt
from app.models.call_screen import CallScreenPublic
from app.models.enums import IntegrationProvider
from app.services.call_screen import call_screen
from app.services.retell import get_retell_call

logger = logging.getLogger(__name__)

router = APIRouter(tags=["calls"], dependencies=[Depends(get_current_user)])


class CallRecording(BaseModel):
    url: str | None = None


@router.get("/calls/{call_id}/screen", response_model=CallScreenPublic)
def get_call_screen(
    session: SessionDep, company_id: CurrentCompany, call_id: uuid.UUID
) -> CallScreenPublic:
    """The single call as its screen shows it: header, timeline and findings.

    The caller shows as their last four digits; secret-looking tool values are masked.
    """
    call = crud.get_call(session=session, call_id=call_id, company_id=company_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    screen = call_screen(session=session, call=call)
    if screen is None:
        raise HTTPException(
            status_code=404, detail="This call has not been converted to a trace yet"
        )
    return screen


@router.get("/calls/{call_id}/recording", response_model=CallRecording)
async def get_call_recording(
    session: SessionDep, company_id: CurrentCompany, call_id: uuid.UUID
) -> CallRecording:
    """Where the call's recording plays from, asked of the voice platform each time:
    its addresses can be signed and expire. Falls back to the stored address."""
    call = crud.get_call(session=session, call_id=call_id, company_id=company_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    if call.integration_id is not None:
        integration = crud.get_integration(
            session=session, integration_id=call.integration_id, company_id=company_id
        )
        if (
            integration is not None
            and integration.provider == IntegrationProvider.RETELL
        ):
            try:
                fresh = await get_retell_call(
                    decrypt(integration.encrypted_api_key), call.external_id
                )
            # Unreachable, refused, or an answer that is not JSON.
            except (HTTPException, ValueError):
                logger.warning(
                    "Retell could not be asked for call %s's recording", call.id
                )
                fresh = None
            if fresh is not None and fresh.raw and fresh.raw.get("recording_url"):
                return CallRecording(url=str(fresh.raw["recording_url"]))
    return CallRecording(url=call.recording_url)
