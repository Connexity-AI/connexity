"""What the Calls page and `list_calls` answer (`app/crud/call_list.py`)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import CallCheckStatus


class WorstFindingPublic(BaseModel):
    title: str = Field(description="The check's name")
    key: str | None = Field(
        default=None, description="What broke, e.g. the tool's name"
    )
    category: str
    severity: str = Field(description="critical or warning")
    found_by: str = Field(description="rule (deterministic) or model")


class IssueMomentPublic(BaseModel):
    at_seconds: float = Field(
        description="When it first happened, from the call's start"
    )
    times: int = Field(description="How many times it happened in the call")


class CallListItemPublic(BaseModel):
    id: uuid.UUID
    started_at: datetime
    agent_id: uuid.UUID
    agent_name: str
    caller_last_four: str | None = Field(
        default=None, description="The caller's last four digits; never the number"
    )
    duration_seconds: int | None = None
    result: CallCheckStatus
    worst_finding: WorstFindingPublic | None = None
    moment: IssueMomentPublic | None = Field(
        default=None,
        description="With an issue filter: where the issue first happened in the call",
    )


class CallTilesPublic(BaseModel):
    calls: int
    failed: int
    degraded: int
    clean: int
    unchecked: int


class CallFilterOption(BaseModel):
    value: str
    label: str


class CallListPublic(BaseModel):
    data: list[CallListItemPublic]
    tiles: CallTilesPublic
    has_more: bool
    period: str
    agents: list[CallFilterOption] = Field(description="The agents to filter by")
    categories: list[CallFilterOption] = Field(
        description="The fixed categories, in order"
    )
    issue: CallFilterOption | None = Field(
        default=None, description="With an issue filter: the issue's id and title"
    )
