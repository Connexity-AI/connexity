"""Postgres-backed scaling helpers for Kubernetes voice workers."""

# Mirrors claim eligibility in app.crud.voice_simulation_job.claim_next_pending_voice_job.
# Used by KEDA postgresql scaler and operator documentation.
CLAIMABLE_VOICE_JOBS_COUNT_SQL = """
SELECT COUNT(*) FROM voice_simulation_job
WHERE status = 'pending'
   OR (
     status IN ('claimed', 'calling')
     AND lease_expires_at IS NOT NULL
     AND lease_expires_at < NOW()
   )
""".strip()
