import uuid

from fastapi import APIRouter, Depends, HTTPException

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import VoiceSimulationJobPublic, VoiceSimulationResultSubmit
from app.services.voice_simulation_results import submit_voice_simulation_result

router = APIRouter(
    prefix="/voice-simulations",
    tags=["voice-simulations"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/results", response_model=VoiceSimulationJobPublic)
def submit_voice_simulation_results(
    session: SessionDep,
    payload: VoiceSimulationResultSubmit,
) -> VoiceSimulationJobPublic:
    job = submit_voice_simulation_result(session=session, payload=payload)
    return VoiceSimulationJobPublic.model_validate(job)


@router.get("/jobs/{job_id}", response_model=VoiceSimulationJobPublic)
def get_voice_simulation_job(
    session: SessionDep,
    job_id: uuid.UUID,
) -> VoiceSimulationJobPublic:
    job = crud.get_voice_simulation_job(session=session, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Voice simulation job not found")
    return VoiceSimulationJobPublic.model_validate(job)
