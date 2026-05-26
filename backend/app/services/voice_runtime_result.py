"""Assemble eval runtime results from completed voice simulation jobs."""

from typing import Any

from app.models import VoiceSimulationJob
from app.models.enums import VoiceSimulationJobStatus
from app.services.eval_runtimes.types import TestCaseRunResult
from app.services.voice_transcript import conversation_turns_from_job_transcript


def assemble_test_case_run_result_from_voice_job(
    job: VoiceSimulationJob,
) -> TestCaseRunResult:
    """Build :class:`TestCaseRunResult` from a completed voice job submission.

    Token and cost fields are empty: the authoritative transcript comes from the
    user-side submission, not from Connexity's simulated caller.
    """
    if job.status != VoiceSimulationJobStatus.COMPLETED:
        msg = f"Voice job must be completed to assemble result (status={job.status.value})"
        raise ValueError(msg)

    transcript = conversation_turns_from_job_transcript(job.normalized_transcript)
    runtime_metadata: dict[str, Any] = {
        "voice_simulation_job_id": str(job.id),
    }
    if job.audio_url:
        runtime_metadata["audio_url"] = job.audio_url
    if job.twilio_call_sid:
        runtime_metadata["twilio_call_sid"] = job.twilio_call_sid

    return TestCaseRunResult(
        transcript=transcript,
        agent_token_usage={},
        platform_token_usage={},
        runtime_metadata=runtime_metadata,
    )
