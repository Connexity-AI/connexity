import pytest

from app.models.agent_contract import ChatMessage
from app.models.enums import TurnRole, VoiceSimulationJobStatus
from app.services.voice_runtime_result import (
    assemble_test_case_run_result_from_voice_job,
)
from app.services.voice_transcript import map_chat_messages_to_conversation_transcript


class _JobStub:
    def __init__(
        self,
        *,
        status: VoiceSimulationJobStatus,
        normalized_transcript: list[dict[str, object]] | None,
        audio_url: str | None = None,
        twilio_call_sid: str | None = None,
        job_id: str = "00000000-0000-0000-0000-000000000001",
    ) -> None:
        self.id = job_id
        self.status = status
        self.normalized_transcript = normalized_transcript
        self.audio_url = audio_url
        self.twilio_call_sid = twilio_call_sid


def test_assemble_test_case_run_result_from_completed_job() -> None:
    messages = [
        ChatMessage(role=TurnRole.USER, content="Hello"),
        ChatMessage(role=TurnRole.ASSISTANT, content="Hi there"),
    ]
    transcript = map_chat_messages_to_conversation_transcript(messages)
    job = _JobStub(
        status=VoiceSimulationJobStatus.COMPLETED,
        normalized_transcript=[t.model_dump(mode="json") for t in transcript],
        audio_url="https://example.com/rec.wav",
        twilio_call_sid="CA999",
    )

    result = assemble_test_case_run_result_from_voice_job(job)  # type: ignore[arg-type]

    assert len(result.transcript) == 2
    assert result.transcript[0].role == TurnRole.USER
    assert result.agent_token_usage == {}
    assert result.platform_token_usage == {}
    assert result.runtime_metadata is not None
    assert result.runtime_metadata["voice_simulation_job_id"] == job.id
    assert result.runtime_metadata["audio_url"] == "https://example.com/rec.wav"
    assert result.runtime_metadata["twilio_call_sid"] == "CA999"


def test_assemble_rejects_incomplete_job() -> None:
    job = _JobStub(
        status=VoiceSimulationJobStatus.WAITING_FOR_RESULT,
        normalized_transcript=None,
    )
    with pytest.raises(ValueError, match="must be completed"):
        assemble_test_case_run_result_from_voice_job(job)  # type: ignore[arg-type]


def test_assemble_rejects_missing_transcript() -> None:
    job = _JobStub(
        status=VoiceSimulationJobStatus.COMPLETED,
        normalized_transcript=None,
    )
    with pytest.raises(ValueError, match="no normalized transcript"):
        assemble_test_case_run_result_from_voice_job(job)  # type: ignore[arg-type]
