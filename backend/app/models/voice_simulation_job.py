import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.agent_contract import ChatMessage
from app.models.enums import VoiceSimulationJobStatus
from app.models.schemas import ConversationTurn

if TYPE_CHECKING:
    from app.models.run import Run
    from app.models.test_case import TestCase
    from app.models.test_case_result import TestCaseResult


class VoiceSimulationJobBase(SQLModel):
    run_id: uuid.UUID = Field(
        foreign_key="run.id",
        index=True,
        description="FK to the parent eval run",
    )
    test_case_id: uuid.UUID = Field(
        foreign_key="test_case.id",
        index=True,
        description="FK to the test case being executed",
    )
    test_case_result_id: uuid.UUID = Field(
        foreign_key="test_case_result.id",
        index=True,
        description="FK to the test case result row for this execution",
    )
    repetition_index: int = Field(
        default=0,
        description="Which repetition of this test case within the run (0-based)",
    )
    status: VoiceSimulationJobStatus = Field(
        default=VoiceSimulationJobStatus.PENDING,
        index=True,
        description="Voice job lifecycle status",
    )
    dtmf_code: str = Field(
        max_length=16,
        index=True,
        description="Connexity DTMF code sent during the call (prefix + body + checksum)",
    )
    agent_phone_number: str = Field(
        max_length=32,
        description="E.164 phone number Connexity dials for this job",
    )
    stt_provider: str = Field(
        max_length=64,
        description="Pipecat STT provider key for the simulated caller",
    )
    stt_model: str = Field(
        max_length=255,
        description="Provider-local STT model id",
    )
    tts_provider: str = Field(
        max_length=64,
        description="Pipecat TTS provider key for the simulated caller",
    )
    tts_model: str = Field(
        max_length=255,
        description="Provider-local TTS model id",
    )
    tts_voice_id: str = Field(
        max_length=255,
        description="Provider voice id for the simulated caller",
    )
    max_call_duration_seconds: int = Field(
        ge=1,
        description="Wall-clock call budget enforced by the voice worker",
    )
    twilio_call_sid: str | None = Field(
        default=None,
        max_length=64,
        index=True,
        description="Twilio call SID once the worker places the call",
    )
    worker_id: str | None = Field(
        default=None,
        max_length=255,
        description="Identifier of the voice worker that claimed this job",
    )
    worker_public_base_url: str | None = Field(
        default=None,
        max_length=2048,
        description=(
            "Public https origin Twilio uses for this job's TwiML and Media Stream "
            "(set by the worker at claim time)"
        ),
    )
    lease_expires_at: datetime | None = Field(
        default=None,
        index=True,
        description="When the worker lease expires; unclaimed jobs may reclaim after expiry",
    )
    claimed_at: datetime | None = Field(
        default=None,
        description="When a worker claimed this job",
    )
    call_started_at: datetime | None = Field(
        default=None,
        description="When the Twilio call was connected",
    )
    call_ended_at: datetime | None = Field(
        default=None,
        description="When the Twilio call ended",
    )
    result_received_at: datetime | None = Field(
        default=None,
        description="When the user-side result submission was accepted",
    )
    audio_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Submitted recording URL after call completion",
    )
    submitted_messages: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column("submitted_messages", JSONB, nullable=True),
        description="Raw OpenAI-format messages from the user-side submission",
    )
    normalized_transcript: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column("normalized_transcript", JSONB, nullable=True),
        description="ConversationTurn[] mapped from submitted messages",
    )
    error_code: str | None = Field(
        default=None,
        max_length=64,
        description="Machine-readable error code when the job fails",
    )
    error_message: str | None = Field(
        default=None,
        description="Human-readable error message when the job fails",
    )


class VoiceSimulationJob(VoiceSimulationJobBase, table=True):
    __tablename__ = "voice_simulation_job"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={
            "server_default": text("now()"),
            "onupdate": lambda: datetime.now(UTC),
        },
    )

    run: "Run" = Relationship()
    test_case: "TestCase" = Relationship()
    test_case_result: "TestCaseResult" = Relationship()


class VoiceSimulationJobCreate(SQLModel):
    run_id: uuid.UUID = Field(description="FK to the parent eval run")
    test_case_id: uuid.UUID = Field(description="FK to the test case being executed")
    test_case_result_id: uuid.UUID = Field(
        description="FK to the test case result row for this execution",
    )
    repetition_index: int = Field(
        default=0,
        description="Repetition index within the run (0-based)",
    )
    dtmf_code: str = Field(description="Connexity DTMF code for this job")
    agent_phone_number: str = Field(description="E.164 agent phone number to dial")
    stt_provider: str = Field(description="STT provider key")
    stt_model: str = Field(description="STT model id")
    tts_provider: str = Field(description="TTS provider key")
    tts_model: str = Field(description="TTS model id")
    tts_voice_id: str = Field(description="TTS voice id")
    max_call_duration_seconds: int = Field(
        ge=1,
        description="Wall-clock call budget enforced by the voice worker",
    )


class VoiceSimulationResultSubmit(SQLModel):
    audio_url: str = Field(
        max_length=2048,
        description="Public URL of the call recording that includes Connexity DTMF tones",
    )
    messages: list[ChatMessage] = Field(
        min_length=1,
        description="OpenAI-format conversation messages from the user-side agent",
    )


class VoiceSimulationJobPublic(SQLModel):
    id: uuid.UUID = Field(description="Unique voice simulation job identifier")
    run_id: uuid.UUID = Field(description="FK to the parent eval run")
    test_case_id: uuid.UUID = Field(description="FK to the test case being executed")
    test_case_result_id: uuid.UUID = Field(
        description="FK to the test case result row for this execution",
    )
    repetition_index: int = Field(
        description="Repetition index within the run (0-based)",
    )
    status: VoiceSimulationJobStatus = Field(description="Voice job lifecycle status")
    dtmf_code: str = Field(description="Connexity DTMF code sent during the call")
    agent_phone_number: str = Field(description="E.164 agent phone number dialed")
    max_call_duration_seconds: int = Field(
        description="Configured maximum call duration in seconds",
    )
    twilio_call_sid: str | None = Field(
        default=None,
        description="Twilio call SID once the worker places the call",
    )
    worker_public_base_url: str | None = Field(
        default=None,
        description="Public worker origin used for this job's Twilio callbacks",
    )
    audio_url: str | None = Field(
        default=None,
        description="Submitted recording URL after call completion",
    )
    submitted_messages: list[dict[str, Any]] | None = Field(
        default=None,
        description="Raw OpenAI-format messages from the user-side submission",
    )
    normalized_transcript: list[dict[str, Any]] | None = Field(
        default=None,
        description="ConversationTurn[] mapped from submitted messages",
    )
    error_code: str | None = Field(
        default=None,
        description="Machine-readable error code when the job fails",
    )
    error_message: str | None = Field(
        default=None,
        description="Human-readable error message when the job fails",
    )
    claimed_at: datetime | None = Field(
        default=None,
        description="When a worker claimed this job",
    )
    call_started_at: datetime | None = Field(
        default=None,
        description="When the Twilio call was connected",
    )
    call_ended_at: datetime | None = Field(
        default=None,
        description="When the Twilio call ended",
    )
    result_received_at: datetime | None = Field(
        default=None,
        description="When the user-side result submission was accepted",
    )
    created_at: datetime = Field(description="When the voice job was created")
    updated_at: datetime = Field(description="When the voice job was last updated")


class VoiceSimulationJobsPublic(SQLModel):
    data: list[VoiceSimulationJobPublic] = Field(
        description="Voice simulation jobs for a run",
    )
    count: int = Field(description="Total number of jobs matching the query")


class VoiceSimulationJobUpdate(SQLModel):
    status: VoiceSimulationJobStatus | None = Field(
        default=None,
        description="Voice job lifecycle status",
    )
    twilio_call_sid: str | None = Field(
        default=None,
        description="Twilio call SID",
    )
    worker_id: str | None = Field(
        default=None,
        description="Voice worker identifier",
    )
    worker_public_base_url: str | None = Field(
        default=None,
        description="Public worker origin used for this job's Twilio callbacks",
    )
    lease_expires_at: datetime | None = Field(
        default=None,
        description="Worker lease expiry",
    )
    claimed_at: datetime | None = Field(
        default=None,
        description="When the job was claimed",
    )
    call_started_at: datetime | None = Field(
        default=None,
        description="When the call started",
    )
    call_ended_at: datetime | None = Field(
        default=None,
        description="When the call ended",
    )
    result_received_at: datetime | None = Field(
        default=None,
        description="When the result was received",
    )
    audio_url: str | None = Field(
        default=None,
        description="Submitted recording URL",
    )
    submitted_messages: list[dict[str, Any]] | None = Field(
        default=None,
        description="Raw OpenAI-format messages from submission",
    )
    normalized_transcript: list[ConversationTurn] | None = Field(
        default=None,
        description="Mapped conversation transcript",
    )
    error_code: str | None = Field(
        default=None,
        description="Machine-readable error code",
    )
    error_message: str | None = Field(
        default=None,
        description="Human-readable error message",
    )
