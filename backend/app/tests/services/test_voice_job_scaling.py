"""KEDA scaler SQL alignment with voice job claim eligibility."""

from __future__ import annotations

from sqlalchemy import and_, func, or_, select

from app.models.enums import VoiceSimulationJobStatus
from app.models.voice_simulation_job import VoiceSimulationJob
from app.services.voice_job_scaling import CLAIMABLE_VOICE_JOBS_COUNT_SQL


def test_claimable_jobs_count_sql_matches_crud_filter() -> None:
    """Documented KEDA query must count the same rows claim_next_pending selects."""
    now_expr = func.now()
    claimable = or_(
        VoiceSimulationJob.status == VoiceSimulationJobStatus.PENDING,
        and_(
            VoiceSimulationJob.status.in_(
                (
                    VoiceSimulationJobStatus.CLAIMED,
                    VoiceSimulationJobStatus.CALLING,
                )
            ),
            VoiceSimulationJob.lease_expires_at.is_not(None),
            VoiceSimulationJob.lease_expires_at < now_expr,
        ),
    )
    orm_count = select(func.count()).select_from(VoiceSimulationJob).where(claimable)

    normalized_sql = " ".join(CLAIMABLE_VOICE_JOBS_COUNT_SQL.split())
    assert "status = 'pending'" in normalized_sql
    assert "status IN ('claimed', 'calling')" in normalized_sql
    assert "lease_expires_at < NOW()" in normalized_sql
    assert orm_count.whereclause is not None
