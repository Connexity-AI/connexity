"""What the agent page's Overview and `get_agent` answer (`app/services/agent_page.py`)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.agent_list import AgentType, Period
from app.models.enums import Platform
from app.models.spec import SpecState


class AgentSystemPublic(BaseModel):
    kind: str = Field(description="What it is, e.g. n8n workflow")
    name: str
    version: str | None = Field(default=None, description="The latest version used")


class AgentLatencyDayPublic(BaseModel):
    day: date
    seconds: float | None = Field(
        default=None, description="The day's average latency; None with no calls"
    )
    calls: int = Field(description="Calls that day with a latency")


class AgentVersionMarkPublic(BaseModel):
    day: date
    label: str = Field(description="'Version 9'")


class AgentPagePublic(BaseModel):
    id: uuid.UUID
    name: str
    platform: Platform | None = None
    type: AgentType | None = None
    live_version: str | None = Field(
        default=None, description="The agent version of its most recent call"
    )
    live_since: datetime | None = Field(
        default=None, description="When the first call on the live version started"
    )
    model: str | None = Field(default=None, description="The live version's model")
    systems: list[AgentSystemPublic] = Field(
        default_factory=list, description="Workflows its tool calls ran in the period"
    )
    spec: SpecState
    period: Period
    calls: int = Field(description="Calls in the period")
    latency_seconds: float | None = Field(
        default=None, description="Average of its calls' latencies in the period"
    )
    latency_calls: int = Field(description="Calls in the period with a latency")
    latency_days: list[AgentLatencyDayPublic] = Field(
        description="Each day of the period, oldest first"
    )
    latency_peak: float | None = Field(
        default=None, description="The highest daily average in the period"
    )
    version_marks: list[AgentVersionMarkPublic] = Field(
        description="Each new agent version that started in the period"
    )
