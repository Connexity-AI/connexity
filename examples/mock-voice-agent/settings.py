"""Runtime settings for the mock voice agent example."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    TWILIO_ACCOUNT_SID: str = Field(default="")
    TWILIO_AUTH_TOKEN: str = Field(default="")
    MOCK_VOICE_AGENT_PUBLIC_BASE_URL: str = Field(default="")

    DEEPGRAM_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")
    ELEVENLABS_API_KEY: str = Field(default="")

    CONNEXITY_API_URL: str = Field(default="http://localhost:8000")
    CONNEXITY_API_TOKEN: str = Field(default="")

    MOCK_VOICE_AGENT_HTTP_HOST: str = Field(default="0.0.0.0")
    MOCK_VOICE_AGENT_HTTP_PORT: int = Field(default=8766)

    MOCK_VOICE_LLM_MODEL: str = Field(default="gpt-4.1-mini")
    MOCK_VOICE_DEEPGRAM_STT_MODEL: str = Field(default="nova-3-general")
    MOCK_VOICE_ELEVENLABS_TTS_MODEL: str = Field(default="eleven_flash_v2_5")
    MOCK_VOICE_ELEVENLABS_VOICE_ID: str = Field(default="21m00Tcm4TlvDq8ikWAM")

    recordings_dir: Path = Field(
        default=Path(__file__).resolve().parent / "recordings",
        alias="MOCK_VOICE_RECORDINGS_DIR",
    )

    def public_base(self) -> str:
        return self.MOCK_VOICE_AGENT_PUBLIC_BASE_URL.strip().rstrip("/")

    def media_stream_wss_url(self) -> str:
        base = self.public_base()
        if base.startswith("https://"):
            host = base.removeprefix("https://")
            return f"wss://{host}/ws"
        if base.startswith("http://"):
            host = base.removeprefix("http://")
            return f"ws://{host}/ws"
        msg = "MOCK_VOICE_AGENT_PUBLIC_BASE_URL must start with http:// or https://"
        raise ValueError(msg)


def get_settings() -> Settings:
    return Settings()
