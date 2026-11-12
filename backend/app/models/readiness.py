"""Readiness: how complete a workspace's setup is (`12-adjustments.md` items 11, 19).

Milestone 1 has only the four Getting started steps. The seven controls come later.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ReadinessStepKey(StrEnum):
    ASSISTANT = "assistant"
    VOICE_PLATFORM = "voice_platform"
    SYNC = "sync"
    FIRST_SCAN = "first_scan"


class ReadinessStepState(StrEnum):
    DONE = "done"
    IN_PROGRESS = "in_progress"
    NOT_STARTED = "not_started"


class ReadinessStep(BaseModel):
    key: ReadinessStepKey
    name: str
    state: ReadinessStepState
    detail: str | None = Field(
        default=None, description="One short fact: the assistant's or platform's name"
    )


class ReadinessPublic(BaseModel):
    steps: list[ReadinessStep]
    done: int = Field(description="Steps done, of the steps shown")
    total: int = Field(description="Steps shown")
    percent: int = Field(description="done / total, rounded to a whole percent")
    first_scan_done: bool
    connect_command: str | None = Field(
        default=None,
        description=(
            "The Claude Code command that connects an assistant, while none is "
            "connected and the MCP address is configured"
        ),
    )
