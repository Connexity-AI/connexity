import uuid

from fastapi import APIRouter, Depends, HTTPException

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import (
    VoiceSimulationJobPublic,
    VoiceSimulationJobsPublic,
    VoiceSimulationResultSubmit,
)
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


@router.get("/runs/{run_id}/jobs", response_model=VoiceSimulationJobsPublic)
def list_voice_simulation_jobs_for_run(
    session: SessionDep,
    run_id: uuid.UUID,
    skip: int = 0,
    limit: int = 500,
) -> VoiceSimulationJobsPublic:
    items, count = crud.list_voice_simulation_jobs(
        session=session,
        run_id=run_id,
        skip=skip,
        limit=limit,
    )
    return VoiceSimulationJobsPublic(
        data=[VoiceSimulationJobPublic.model_validate(job) for job in items],
        count=count,
    )


@router.get("/jobs/{job_id}", response_model=VoiceSimulationJobPublic)
def get_voice_simulation_job(
    session: SessionDep,
    job_id: uuid.UUID,
) -> VoiceSimulationJobPublic:
    job = crud.get_voice_simulation_job(session=session, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Voice simulation job not found")
    return VoiceSimulationJobPublic.model_validate(job)
