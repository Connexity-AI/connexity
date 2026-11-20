"""What the agent page's Overview and `get_agent` answer (`app/services/agent_page.py`)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.agent_list import AgentType, Period
from app.models.enums import Platform
from app.models.score import ScorePublic
from app.models.spec import SpecState


class AgentSystemPublic(BaseModel):
    kind: str = Field(description="What it is, e.g. n8n workflow")
    name: str
    version: str | None = Field(default=None, description="The latest version used")


class AgentLatencyDayPublic(BaseModel):
    day: date
    p50: float | None = Field(
        default=None, description="The day's p50 over its replies; None without one"
    )
    replies: int = Field(description="Replies that day: times the agent answered")
    score: int | None = Field(
        default=None,
        description="The day's score over its checked calls, by the Score's formula; "
        "None without a checked call or before onboarding is complete",
    )
    checked_calls: int = Field(
        default=0, description="Checked calls that day: the day's score rests on them"
    )


class AgentVersionMarkPublic(BaseModel):
    day: date
    label: str = Field(description="'Version 9'")


class AgentVersionOptionPublic(BaseModel):
    version: str
    calls: int = Field(description="Its calls, all time")
    live: bool = Field(default=False, description="The version of the latest call")


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
    latency_p50: float | None = Field(
        default=None, description="p50 over every reply in the period, in seconds"
    )
    latency_p95: float | None = Field(
        default=None, description="p95 over every reply in the period, in seconds"
    )
    latency_replies: int = Field(
        description="Replies in the period the latency rests on"
    )
    latency_days: list[AgentLatencyDayPublic] = Field(
        description="Each day of the period, oldest first, with its p50"
    )
    latency_peak: float | None = Field(
        default=None, description="The highest daily p50 in the period"
    )
    version_marks: list[AgentVersionMarkPublic] = Field(
        description="Each new agent version that started in the period"
    )
    score: ScorePublic | None = Field(
        default=None,
        description="The agent's score for the period and its change (why_none when it "
        "has none); on the picked version's calls with a version",
    )
    critical_issues: int = Field(
        default=0,
        description="Open or reopened critical issues that showed in the period; on "
        "the picked version's calls with a version",
    )
    open_issues: int = Field(
        default=0,
        description="Open or reopened issues that showed in the period, as the Issues "
        "page's Open tile counts them; on the picked version's calls with a version",
    )
    versions: list[AgentVersionOptionPublic] = Field(
        default_factory=list,
        description="Every agent version that has a call, latest call first",
    )
    version: str | None = Field(
        default=None,
        description="The version the numbers are filtered to; none for all versions",
    )
    version_days: list[date] = Field(
        default_factory=list,
        description="With a version: the period's days that had calls on it",
    )
