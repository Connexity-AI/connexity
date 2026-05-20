from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app import crud
from app.models import VoiceSimulationJobCreate, VoiceSimulationJobUpdate
from app.models.enums import VoiceSimulationJobStatus
from app.models.schemas import ConversationTurn, TurnRole
from app.services.dtmf import format_dtmf_code
from app.tests.utils.eval import (
    create_test_case_fixture,
    create_test_case_result_fixture,
    create_test_eval_config,
    create_test_run,
    eval_config_members,
)

_CANCELLABLE = (
    VoiceSimulationJobStatus.PENDING,
    VoiceSimulationJobStatus.CLAIMED,
    VoiceSimulationJobStatus.CALLING,
    VoiceSimulationJobStatus.WAITING_FOR_RESULT,
)


@pytest.fixture(autouse=True)
def _isolate_voice_jobs(db: Session) -> None:
    """Session-scoped DB shares state across tests; clear active voice jobs."""
    jobs, _count = crud.list_voice_simulation_jobs(session=db, limit=10_000)
    for job in jobs:
        if job.status in _CANCELLABLE:
            crud.update_voice_simulation_job(
                session=db,
                db_job=job,
                job_in=VoiceSimulationJobUpdate(
                    status=VoiceSimulationJobStatus.CANCELLED,
                ),
            )


def _voice_job_create(
    *,
    run_id,
    test_case_id,
    test_case_result_id,
    dtmf_code: str = format_dtmf_code(body=24),
) -> VoiceSimulationJobCreate:
    return VoiceSimulationJobCreate(
        run_id=run_id,
        test_case_id=test_case_id,
        test_case_result_id=test_case_result_id,
        dtmf_code=dtmf_code,
        agent_phone_number="+15551234567",
        stt_provider="deepgram",
        stt_model="nova-3",
        tts_provider="elevenlabs",
        tts_model="eleven_flash_v2_5",
        tts_voice_id="test-voice",
    )


def _setup_voice_job_context(db: Session):
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(test_case.id))
    run = create_test_run(
        db, agent_id=eval_config.agent_id, eval_config_id=eval_config.id
    )
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    return run, test_case, result


def test_create_voice_simulation_job(db: Session) -> None:
    run, test_case, result = _setup_voice_job_context(db)
    job = crud.create_voice_simulation_job(
        session=db,
        job_in=_voice_job_create(
            run_id=run.id,
            test_case_id=test_case.id,
            test_case_result_id=result.id,
        ),
    )
    assert job.id is not None
    assert job.status == VoiceSimulationJobStatus.PENDING
    assert job.dtmf_code == format_dtmf_code(body=24)
    assert job.worker_id is None


def test_get_and_list_voice_simulation_jobs(db: Session) -> None:
    run, test_case, result = _setup_voice_job_context(db)
    job = crud.create_voice_simulation_job(
        session=db,
        job_in=_voice_job_create(
            run_id=run.id,
            test_case_id=test_case.id,
            test_case_result_id=result.id,
        ),
    )
    fetched = crud.get_voice_simulation_job(session=db, job_id=job.id)
    assert fetched is not None
    assert fetched.id == job.id

    items, count = crud.list_voice_simulation_jobs(session=db, run_id=run.id)
    assert count == 1
    assert items[0].run_id == run.id


def test_update_voice_simulation_job(db: Session) -> None:
    run, test_case, result = _setup_voice_job_context(db)
    job = crud.create_voice_simulation_job(
        session=db,
        job_in=_voice_job_create(
            run_id=run.id,
            test_case_id=test_case.id,
            test_case_result_id=result.id,
        ),
    )
    updated = crud.update_voice_simulation_job(
        session=db,
        db_job=job,
        job_in=VoiceSimulationJobUpdate(
            status=VoiceSimulationJobStatus.WAITING_FOR_RESULT,
            twilio_call_sid="CA123",
            normalized_transcript=[
                ConversationTurn(
                    index=0,
                    role=TurnRole.USER,
                    content="hello",
                    timestamp=datetime.now(UTC),
                ),
            ],
        ),
    )
    assert updated.status == VoiceSimulationJobStatus.WAITING_FOR_RESULT
    assert updated.twilio_call_sid == "CA123"
    assert updated.normalized_transcript is not None
    assert updated.normalized_transcript[0]["role"] == "user"


def test_claim_next_pending_voice_job(db: Session) -> None:
    run, test_case, result = _setup_voice_job_context(db)
    crud.create_voice_simulation_job(
        session=db,
        job_in=_voice_job_create(
            run_id=run.id,
            test_case_id=test_case.id,
            test_case_result_id=result.id,
            dtmf_code=format_dtmf_code(body=1),
        ),
    )
    claimed = crud.claim_next_pending_voice_job(
        session=db,
        worker_id="worker-a",
        lease_seconds=60,
    )
    assert claimed is not None
    assert claimed.dtmf_code == format_dtmf_code(body=1)
    assert claimed.status == VoiceSimulationJobStatus.CLAIMED
    assert claimed.worker_id == "worker-a"
    assert claimed.claimed_at is not None
    assert claimed.lease_expires_at is not None

    second_claim = crud.claim_next_pending_voice_job(
        session=db,
        worker_id="worker-b",
        lease_seconds=60,
    )
    assert second_claim is None


def test_claim_reclaims_expired_lease(db: Session) -> None:
    run, test_case, result = _setup_voice_job_context(db)
    job = crud.create_voice_simulation_job(
        session=db,
        job_in=_voice_job_create(
            run_id=run.id,
            test_case_id=test_case.id,
            test_case_result_id=result.id,
            dtmf_code=format_dtmf_code(body=2),
        ),
    )
    past = datetime.now(UTC) - timedelta(seconds=30)
    crud.update_voice_simulation_job(
        session=db,
        db_job=job,
        job_in=VoiceSimulationJobUpdate(
            status=VoiceSimulationJobStatus.CALLING,
            worker_id="stale-worker",
            lease_expires_at=past,
            claimed_at=past,
        ),
    )
    reclaimed = crud.claim_next_pending_voice_job(
        session=db,
        worker_id="worker-b",
        lease_seconds=120,
    )
    assert reclaimed is not None
    assert reclaimed.id == job.id
    assert reclaimed.worker_id == "worker-b"
    assert reclaimed.status == VoiceSimulationJobStatus.CLAIMED


def test_get_voice_simulation_job_by_dtmf(db: Session) -> None:
    run, test_case, result = _setup_voice_job_context(db)
    job = crud.create_voice_simulation_job(
        session=db,
        job_in=_voice_job_create(
            run_id=run.id,
            test_case_id=test_case.id,
            test_case_result_id=result.id,
            dtmf_code=format_dtmf_code(body=3),
        ),
    )
    crud.update_voice_simulation_job(
        session=db,
        db_job=job,
        job_in=VoiceSimulationJobUpdate(
            status=VoiceSimulationJobStatus.WAITING_FOR_RESULT,
        ),
    )
    match = crud.get_voice_simulation_job_by_dtmf(
        session=db, dtmf_code=format_dtmf_code(body=3)
    )
    assert match is not None
    assert match.dtmf_code == format_dtmf_code(body=3)


def test_cancel_voice_jobs_for_run(db: Session) -> None:
    run, test_case, result = _setup_voice_job_context(db)
    crud.create_voice_simulation_job(
        session=db,
        job_in=_voice_job_create(
            run_id=run.id,
            test_case_id=test_case.id,
            test_case_result_id=result.id,
            dtmf_code=format_dtmf_code(body=4),
        ),
    )
    cancelled = crud.cancel_voice_jobs_for_run(session=db, run_id=run.id)
    assert cancelled == 1
    items, _count = crud.list_voice_simulation_jobs(session=db, run_id=run.id)
    assert items[0].status == VoiceSimulationJobStatus.CANCELLED
