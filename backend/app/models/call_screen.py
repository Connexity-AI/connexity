"""What the single call screen and `get_call` answer (`app/services/call_screen.py`).

Shaped for the screen, not the raw trace: the caller's full number and the platform's
payload are never sent, and secret-looking values in tool calls are masked.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import CallCheckStatus


class KeyValue(BaseModel):
    key: str
    value: str


class CallScreenEntry(BaseModel):
    kind: Literal["turn", "tool"]
    at_seconds: float
    end_seconds: float | None = None
    # A turn.
    speaker: Literal["agent", "caller", "other"] | None = None
    text: str | None = None
    # A tool call.
    tool: str | None = None
    status: Literal["ok", "failed", "timed out", "no result"] | None = None
    duration_ms: int | None = None
    arguments: list[KeyValue] = Field(default_factory=list)
    result: list[KeyValue] = Field(default_factory=list)
    workflow: str | None = Field(
        default=None, description="The n8n workflow it ran: 'quote-lookup v7 · 9 steps'"
    )
    # What the checks found on this entry.
    finding_ids: list[uuid.UUID] = Field(default_factory=list)


class CallScreenFinding(BaseModel):
    id: uuid.UUID
    at_seconds: float
    text: str = Field(description="The check's title and what broke")
    category: str
    severity: Literal["critical", "warning"]
    found_by: Literal["rule", "model"]
    entry_index: int | None = Field(
        default=None, description="The timeline entry it sits on"
    )


class CallScreenPublic(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    started_at: datetime
    duration_seconds: int | None = None
    caller_last_four: str | None = Field(
        default=None, description="The caller's last four digits; never the number"
    )
    result: CallCheckStatus
    version: str | None = None
    has_recording: bool
    entries: list[CallScreenEntry]
    findings: list[CallScreenFinding] = Field(
        description="Worst first: critical, then by time"
    )
