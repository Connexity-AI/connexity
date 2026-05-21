from typing import Literal

from sqlmodel import Field, SQLModel


class ErrorResponse(SQLModel):
    detail: str
    code: str
    status: int


class VoiceSimulationConfigPublic(SQLModel):
    deployment_mode: Literal["local", "kubernetes"] = Field(
        description="Voice deployment profile controlling concurrency limits",
    )
    max_concurrency: int = Field(
        description="Maximum parallel voice calls allowed for this deployment",
    )
    voice_runtime_available: bool = Field(
        description="True when Twilio credentials are configured for voice runs",
    )
    result_submission_path: str = Field(
        description="Relative API path for user-side voice result submission",
    )
    default_call_duration_seconds: int = Field(
        description="Default max call duration when omitted from RunConfig",
    )
    max_call_duration_seconds: int = Field(
        description="Upper bound for RunConfig max_call_duration_seconds",
    )


class ConfigPublic(SQLModel):
    project_name: str
    api_version: str
    environment: Literal["local", "staging", "production"]
    docs_url: str
    default_llm_model: str
    voice_simulation: VoiceSimulationConfigPublic | None = Field(
        default=None,
        description="Voice simulation settings and availability for the UI",
    )
