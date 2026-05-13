from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ImportedPlatformConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_prompt: str
    agent_model: str
    agent_provider: str | None = None
    agent_temperature: float | None = None
    tools: list[dict[str, Any]] | None = Field(default=None)
