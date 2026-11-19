"""What the Agents page answers (`app/services/agent_list.py`)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import Platform
from app.models.spec import SpecState

AgentType = Literal["single_prompt", "conversational_flow"]
Period = Literal["7d", "30d", "90d"]


class AgentListItemPublic(BaseModel):
    id: uuid.UUID
    name: str
    platform: Platform | None = None
    type: AgentType | None = Field(
        default=None,
        description="From its current version in Connexity's catalogue; None if unknown",
    )
    calls: int = Field(description="Calls in the period")
    latency_p50: float | None = Field(
        default=None, description="p50 over every reply in the period, in seconds"
    )
    latency_p95: float | None = Field(
        default=None, description="p95 over every reply in the period, in seconds"
    )
    score: int | None = Field(
        default=None,
        description="0 to 100 for the period; none before onboarding is complete or "
        "with no checked call",
    )
    score_change: int | None = Field(
        default=None, description="Against the previous period of the same length"
    )
    critical_issues: int = Field(
        default=0,
        description="Open or reopened critical issues that showed in the period",
    )
    live_version: str | None = Field(
        default=None, description="The agent version of its most recent call"
    )
    live_since: datetime | None = Field(
        default=None, description="When the first call on that version started"
    )
    spec: SpecState = Field(description="none, current, or needs_review")


class AgentListPublic(BaseModel):
    data: list[AgentListItemPublic] = Field(
        description="Lowest score first; agents without a score after, most calls "
        "first, then by name"
    )
    period: Period
