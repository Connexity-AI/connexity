"""What the single call screen and `get_call` answer (`app/services/call_screen.py`).

Shaped for the screen, not the raw trace: the caller's full number and the platform's
payload are never sent, and secret-looking values in tool calls are masked.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import CallCheckStatus, CheckKind, RuleOutcome
from app.services.grading import GRADING_MIN_AGENT_WORDS


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
    found_by: CheckKind
    entry_index: int | None = Field(
        default=None, description="The timeline entry it sits on"
    )
    issue_id: uuid.UUID | None = Field(default=None, description="The issue it joins")
    probability: float | None = Field(
        default=None,
        description="For a broken spec rule: the classifier's probability. Such a "
        "finding judges the whole call and has no moment in it",
    )


class SimulatedVerdictPublic(BaseModel):
    key: str
    text: str | None = Field(
        default=None, description="The rule in the spec version the run judged"
    )
    critical: bool = False
    outcome: RuleOutcome
    reason: str | None = None
    entry_indexes: list[int] = Field(
        default_factory=list, description="The timeline entries the verdict rests on"
    )


class SimulatedLinePublic(BaseModel):
    """What makes a simulated call one: its scenario and the rules it was judged on."""

    run_id: uuid.UUID
    scenario_name: str
    edited: bool = Field(
        default=False,
        description="The tested draft was edited under the same version number",
    )
    verdicts: list[SimulatedVerdictPublic] = Field(
        default_factory=list, description="Failed first"
    )
    stopped: str | None = Field(
        default=None,
        description="Why the conversation stopped before it could be judged",
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
    graded: bool = Field(
        default=True,
        description=f"False when the agent spoke fewer than {GRADING_MIN_AGENT_WORDS} words: "
        "the call is never "
        "judged against the spec, and with nothing found it does not count in the score",
    )
    not_graded_reason: str | None = Field(
        default=None, description="Why the call is not graded; none when it is"
    )
    agent_words: int | None = Field(
        default=None,
        description="How many words the agent spoke; none on a simulated call",
    )
    version: str | None = None
    has_recording: bool
    entries: list[CallScreenEntry]
    findings: list[CallScreenFinding] = Field(
        description="Worst first: critical, then by time"
    )
    simulated: SimulatedLinePublic | None = Field(
        default=None,
        description="Set on a simulated call: no recording, no timing, no caller",
    )
