"""What the Issues page and `list_issues` answer (`app/services/issue_list.py`)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.call_list import CallFilterOption
from app.models.enums import IssueState

IssueStatusFilter = Literal["open", "reopened", "resolved", "archived"]
IssuePeriod = Literal["7d", "30d", "90d"]


class IssueTilesPublic(BaseModel):
    open: int = Field(description="Open and reopened issues")
    critical: int = Field(description="Open or reopened issues that are Critical")
    reopened: int
    resolved: int = Field(description="Issues resolved in the period")
    calls_affected: int = Field(
        description="Calls in the period with a finding from an open or reopened issue"
    )
    calls: int = Field(description="All calls in the period")


class IssueListItemPublic(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    title: str = Field(description="The check's name and, if it has one, the key")
    check_type: str
    key: str | None = Field(default=None, description="What broke, e.g. a tool's name")
    category: str = Field(description="The category's key")
    severity: Literal["critical", "warning"]
    found_by: Literal["rule", "model"] = Field(
        description="rule: deterministic code over the call; model: a classifier or judge"
    )
    state: IssueState
    resolved_version: str | None = None
    calls_affected: int = Field(description="Calls in the period it was found on")
    calls_total: int = Field(description="The agent's calls in the period")
    last_seen_at: datetime | None = Field(
        default=None, description="When the latest call it was found on started"
    )


class IssueGroupPublic(BaseModel):
    category: CallFilterOption = Field(description="The category's key and name")
    issue_count: int
    calls_affected: int = Field(
        description="Distinct calls in the period any issue in the group was found on"
    )
    critical: int = Field(description="Open or reopened Critical issues in the group")
    issues: list[IssueListItemPublic] = Field(description="Worst first")


class IssueListPublic(BaseModel):
    tiles: IssueTilesPublic
    groups: list[IssueGroupPublic] = Field(
        description="In the categories' fixed order; empty categories are left out"
    )
    total: int = Field(description="Issues matching the search and filters")
    truncated: bool = Field(description="True when more matched than were returned")
    period: IssuePeriod
    status: IssueStatusFilter
    agents: list[CallFilterOption] = Field(description="The agents to filter by")
    categories: list[CallFilterOption] = Field(
        description="The fixed categories, in order"
    )
