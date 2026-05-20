import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_
from sqlmodel import Session, col, select

from app.models import (
    VoiceSimulationJob,
    VoiceSimulationJobCreate,
    VoiceSimulationJobUpdate,
)
from app.models.enums import VoiceSimulationJobStatus

_ACTIVE_CLAIM_STATUSES = (
    VoiceSimulationJobStatus.CLAIMED,
    VoiceSimulationJobStatus.CALLING,
)

_CANCELLABLE_STATUSES = (
    VoiceSimulationJobStatus.PENDING,
    VoiceSimulationJobStatus.CLAIMED,
    VoiceSimulationJobStatus.CALLING,
    VoiceSimulationJobStatus.WAITING_FOR_RESULT,
)

_RESULT_MATCH_STATUSES = (
    VoiceSimulationJobStatus.CALLING,
    VoiceSimulationJobStatus.WAITING_FOR_RESULT,
)


def create_voice_simulation_job(
    *, session: Session, job_in: VoiceSimulationJobCreate
) -> VoiceSimulationJob:
    db_obj = VoiceSimulationJob.model_validate(job_in)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_voice_simulation_job(
    *, session: Session, job_id: uuid.UUID
) -> VoiceSimulationJob | None:
    return session.get(VoiceSimulationJob, job_id)


def get_voice_simulation_job_by_dtmf(
    *,
    session: Session,
    dtmf_code: str,
    statuses: tuple[VoiceSimulationJobStatus, ...] | None = _RESULT_MATCH_STATUSES,
) -> VoiceSimulationJob | None:
    statement = select(VoiceSimulationJob).where(
        VoiceSimulationJob.dtmf_code == dtmf_code,
    )
    if statuses is not None:
        statement = statement.where(col(VoiceSimulationJob.status).in_(statuses))
    statement = (
        statement.order_by(VoiceSimulationJob.created_at.desc()).limit(1)
    )
    return session.exec(statement).first()


def list_voice_simulation_jobs(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    run_id: uuid.UUID | None = None,
    test_case_id: uuid.UUID | None = None,
    test_case_result_id: uuid.UUID | None = None,
    status: VoiceSimulationJobStatus | None = None,
) -> tuple[list[VoiceSimulationJob], int]:
    statement = select(VoiceSimulationJob)
    count_statement = select(func.count()).select_from(VoiceSimulationJob)

    if run_id is not None:
        statement = statement.where(VoiceSimulationJob.run_id == run_id)
        count_statement = count_statement.where(VoiceSimulationJob.run_id == run_id)
    if test_case_id is not None:
        statement = statement.where(VoiceSimulationJob.test_case_id == test_case_id)
        count_statement = count_statement.where(
            VoiceSimulationJob.test_case_id == test_case_id
        )
    if test_case_result_id is not None:
        statement = statement.where(
            VoiceSimulationJob.test_case_result_id == test_case_result_id
        )
        count_statement = count_statement.where(
            VoiceSimulationJob.test_case_result_id == test_case_result_id
        )
    if status is not None:
        statement = statement.where(VoiceSimulationJob.status == status)
        count_statement = count_statement.where(VoiceSimulationJob.status == status)

    count = session.exec(count_statement).one()
    items = list(
        session.exec(
            statement.order_by(VoiceSimulationJob.created_at).offset(skip).limit(limit)
        ).all()
    )
    return items, count


def update_voice_simulation_job(
    *,
    session: Session,
    db_job: VoiceSimulationJob,
    job_in: VoiceSimulationJobUpdate,
) -> VoiceSimulationJob:
    update_data = job_in.model_dump(exclude_unset=True)
    if (
        "normalized_transcript" in update_data
        and job_in.normalized_transcript is not None
    ):
        update_data["normalized_transcript"] = [
            t.model_dump(mode="json") for t in job_in.normalized_transcript
        ]
    db_job.sqlmodel_update(update_data)
    session.add(db_job)
    session.commit()
    session.refresh(db_job)
    return db_job


def claim_next_pending_voice_job(
    *,
    session: Session,
    worker_id: str,
    lease_seconds: int,
) -> VoiceSimulationJob | None:
    now = datetime.now(UTC)
    claimable = or_(
        VoiceSimulationJob.status == VoiceSimulationJobStatus.PENDING,
        and_(
            col(VoiceSimulationJob.status).in_(_ACTIVE_CLAIM_STATUSES),
            VoiceSimulationJob.lease_expires_at.is_not(None),
            VoiceSimulationJob.lease_expires_at < now,
        ),
    )
    statement = (
        select(VoiceSimulationJob)
        .where(claimable)
        .order_by(VoiceSimulationJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = session.exec(statement).first()
    if job is None:
        session.commit()
        return None

    lease_expires_at = now + timedelta(seconds=lease_seconds)
    job.status = VoiceSimulationJobStatus.CLAIMED
    job.worker_id = worker_id
    job.claimed_at = now
    job.lease_expires_at = lease_expires_at
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def cancel_voice_jobs_for_run(*, session: Session, run_id: uuid.UUID) -> int:
    statement = select(VoiceSimulationJob).where(
        VoiceSimulationJob.run_id == run_id,
        col(VoiceSimulationJob.status).in_(_CANCELLABLE_STATUSES),
    )
    jobs = list(session.exec(statement).all())
    for job in jobs:
        job.status = VoiceSimulationJobStatus.CANCELLED
        session.add(job)
    if jobs:
        session.commit()
    return len(jobs)
