"""What one issue's page and `get_issue` answer (`app/services/issue_page.py`)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.call_list import CallFilterOption, IssueMomentPublic
from app.models.enums import CallCheckStatus, IssueState

ArchiveDuration = Literal["until_spike", "forever"]


class IssueArchivePublic(BaseModel):
    by: str = Field(description="The person who archived it or approved it")
    assistant: str | None = Field(
        default=None, description="The assistant that archived it with their approval"
    )
    at: datetime
    duration: ArchiveDuration
    reason: str | None = None


class IssuePageTilesPublic(BaseModel):
    calls_affected: int = Field(description="Calls in the last 30 days it was found on")
    calls_total: int = Field(description="The agent's calls in the last 30 days")
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None


class IssueFoundPublic(BaseModel):
    at: datetime = Field(description="When the first call it was found on started")
    call_id: uuid.UUID
    caller_last_four: str | None = None


class IssueFixedPublic(BaseModel):
    version: str | None = None
    at: datetime


class IssueChainPublic(BaseModel):
    found: IssueFoundPublic | None = None
    fixed: IssueFixedPublic | None = Field(
        default=None, description="Set while the issue is resolved"
    )


class IssueDayPublic(BaseModel):
    day: date
    calls: int


class IssueMarkPublic(BaseModel):
    day: date
    kind: Literal["version", "archived", "spiked"]
    label: str = Field(description="'Version 9', 'Archived by Alex', 'Spiked'")


class IssueAffectedCallPublic(BaseModel):
    call_id: uuid.UUID
    started_at: datetime
    caller_last_four: str | None = Field(
        default=None, description="The caller's last four digits; never the number"
    )
    duration_seconds: int | None = None
    result: CallCheckStatus
    moment: IssueMomentPublic


class IssueHistoryPublic(BaseModel):
    kind: Literal[
        "opened", "archived", "unarchived", "spiked", "resolved", "reopened", "changed"
    ]
    what: str = Field(description="'Archived', 'Came back: it spiked'")
    by: str | None = Field(
        default=None, description="The person; None for Connexity's own decision"
    )
    assistant: str | None = None
    at: datetime
    reason: str | None = None
    duration: ArchiveDuration | None = None


class IssuePagePublic(BaseModel):
    id: uuid.UUID
    title: str = Field(description="The check's name and, if it has one, the key")
    check_type: str
    key: str | None = None
    agent_id: uuid.UUID
    agent_name: str
    category: CallFilterOption
    severity: Literal["critical", "warning"]
    found_by: Literal["rule", "model"]
    state: IssueState
    resolved_version: str | None = None
    archive: IssueArchivePublic | None = Field(
        default=None, description="While archived: who, when, how long and why"
    )
    tiles: IssuePageTilesPublic
    chain: IssueChainPublic
    days: list[IssueDayPublic] = Field(description="The last 30 days, oldest first")
    marks: list[IssueMarkPublic] = Field(description="Marks on the chart, oldest first")
    peak: int = Field(description="The most calls on one day in the period")
    affected_calls: list[IssueAffectedCallPublic] = Field(
        description="The latest 10 calls in the period, newest first, one row per call"
    )
    history: list[IssueHistoryPublic] = Field(
        description="Decisions about it, newest first, ending with when it was opened"
    )
