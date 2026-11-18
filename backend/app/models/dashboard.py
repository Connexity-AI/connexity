"""The Dashboard: where a founder stands with their voice agents (`services/dashboard.py`,
design `designs/screens/Connexity Home.dc.html`)."""

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.models.call_list import CallFilterOption
from app.models.score import ScorePublic

AreaStatus = Literal["critical", "warning", "healthy", "not_checked"]


class DashboardStep(BaseModel):
    key: Literal["scan", "spec", "answers", "complete"]
    label: str = Field(description="'Scan', 'Spec', 'Answers 17 of 20', 'Complete'")
    done: bool


class DashboardOnboarding(BaseModel):
    """Shown while onboarding runs; gone once every step is done."""

    steps: list[DashboardStep]
    areas_checked: int
    areas_total: int


class DashboardLatency(BaseModel):
    p50: float | None = Field(default=None, description="Seconds")
    p95: float | None = Field(default=None, description="Seconds")
    answers: int = Field(description="Reply gaps they rest on")


class DashboardDay(BaseModel):
    day: date
    calls: int
    failed: int
    degraded: int


class DashboardMark(BaseModel):
    day: date
    version: str
    agent_name: str


class DashboardArea(BaseModel):
    key: str = Field(description="The category's key")
    name: str
    status: AreaStatus
    waits_for: str | None = Field(
        default=None, description="For an area not checked yet: what it waits for"
    )
    failed: int = 0
    degraded: int = 0
    share: float | None = Field(
        default=None,
        description="Failed and degraded calls of the area, of the period's calls (0-1)",
    )
    top_issue_id: uuid.UUID | None = None
    top_issue_title: str | None = None


class DashboardPublic(BaseModel):
    period: str
    agent_id: uuid.UUID | None = Field(
        default=None, description="The agent shown; none for all agents"
    )
    agents: list[CallFilterOption] = Field(description="The agents to pick from")
    agents_counted: int
    calls: int
    onboarding: DashboardOnboarding | None = None
    score: ScorePublic
    failed: int
    failed_share: float | None = None
    degraded: int
    degraded_share: float | None = None
    latency: DashboardLatency
    days: list[DashboardDay] = Field(
        description="Every day of the period, oldest first"
    )
    marks: list[DashboardMark]
    areas: list[DashboardArea] = Field(
        description="Every fixed area: critical, warning, healthy, then not checked yet"
    )
