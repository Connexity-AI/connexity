from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import Session

from app import crud
from app.models import (
    VoiceSimulationJob,
    VoiceSimulationJobUpdate,
    VoiceSimulationResultSubmit,
)
from app.models.enums import VoiceSimulationJobStatus
from app.services.dtmf import decode_dtmf_from_audio_url
from app.services.voice_transcript import map_chat_messages_to_conversation_transcript

_ACCEPTING_STATUSES = (
    VoiceSimulationJobStatus.CALLING,
    VoiceSimulationJobStatus.WAITING_FOR_RESULT,
)


def submit_voice_simulation_result(
    *,
    session: Session,
    payload: VoiceSimulationResultSubmit,
) -> VoiceSimulationJob:
    decode_result = decode_dtmf_from_audio_url(payload.audio_url)
    if not decode_result.success:
        raise HTTPException(
            status_code=400,
            detail=decode_result.error_message or "DTMF decode failed",
        )

    assert decode_result.digits is not None
    job = crud.get_voice_simulation_job_by_dtmf(
        session=session,
        dtmf_code=decode_result.digits,
        statuses=None,
    )
    if job is None:
        raise HTTPException(
            status_code=404,
            detail="No pending voice job matches decoded DTMF code",
        )

    submitted_messages = [
        message.model_dump(mode="json") for message in payload.messages
    ]
    normalized_transcript = map_chat_messages_to_conversation_transcript(
        payload.messages,
        base_timestamp=datetime.now(UTC),
    )

    if job.status == VoiceSimulationJobStatus.COMPLETED:
        if (
            job.audio_url == payload.audio_url
            and job.submitted_messages == submitted_messages
        ):
            return job
        raise HTTPException(
            status_code=409,
            detail="Voice job already completed with a different submission",
        )

    if job.status not in _ACCEPTING_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Voice job is not accepting results (status={job.status.value})",
        )

    return crud.update_voice_simulation_job(
        session=session,
        db_job=job,
        job_in=VoiceSimulationJobUpdate(
            status=VoiceSimulationJobStatus.COMPLETED,
            audio_url=payload.audio_url,
            submitted_messages=submitted_messages,
            normalized_transcript=normalized_transcript,
            result_received_at=datetime.now(UTC),
        ),
    )
