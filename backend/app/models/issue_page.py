"""What one issue's page and `get_issue` answer (`app/services/issue_page.py`)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.call_list import CallFilterOption, IssueMomentPublic
from app.models.enums import CallCheckStatus, CheckKind, IssueState
from app.models.spec import RuleClarificationPublic

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
    live_at: datetime | None = Field(
        default=None,
        description="When the fix's version went live; none while it has not",
    )


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
    moment: IssueMomentPublic | None = Field(
        default=None,
        description="Where it first happened in the call; none for a broken spec rule "
        "with no moment (found by the classifier alone, or the LLM named no line)",
    )
    probability: float | None = Field(
        default=None,
        description="For a broken spec rule the classifier found: its probability on "
        "this call",
    )
    reason: str | None = Field(
        default=None,
        description="For a broken spec rule an LLM confirmed or found: why, in its "
        "words",
    )


class IssueHistoryPublic(BaseModel):
    kind: Literal[
        "opened",
        "archived",
        "unarchived",
        "spiked",
        "resolved",
        "live",
        "reopened",
        "changed",
        "marked_false",
        "counted_again",
        "brought_back",
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
    found_by: CheckKind
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
    whole_call: bool = Field(
        default=False,
        description="A broken spec rule: its findings may judge the whole call, with "
        "no moment and no reason",
    )
    false_positives: int = Field(
        default=0,
        description="Its findings marked as false positives, all time: shown on no call "
        "and counted nowhere",
    )
    dismissed: int = Field(
        default=0,
        description="For a broken spec rule: flags the LLM step dismissed on its rule, "
        "all time; they never became findings",
    )
    found_how: Literal["classifier", "confirmed", "llm"] | None = Field(
        default=None,
        description="For a broken spec rule, from its newest finding: the classifier "
        "alone, the classifier confirmed by an LLM, or an LLM alone",
    )
    clarifications: list[RuleClarificationPublic] = Field(
        default_factory=list,
        description="For a broken spec rule: the clarifications in force on the rule",
    )


class NotCountedRow(BaseModel):
    """A finding marked as a false positive, or a flag the LLM step dismissed."""

    finding_id: uuid.UUID | None = Field(
        default=None, description="The marked finding; none for a dismissed flag"
    )
    call_id: uuid.UUID
    started_at: datetime
    caller_last_four: str | None = Field(
        default=None, description="The caller's last four digits; never the number"
    )
    at_seconds: float | None = Field(
        default=None, description="Its moment in the call, when it has one"
    )
    by: str | None = Field(default=None, description="The person who marked it")
    assistant: str | None = Field(
        default=None, description="The assistant that marked it for that person"
    )
    at: datetime | None = Field(default=None, description="When it was marked")
    reason: str | None = Field(
        default=None, description="Why it was marked, or the model's reason to dismiss"
    )
    clarification: str | None = Field(
        default=None, description="The clarification the marking rests on"
    )
    approved_by: str | None = Field(
        default=None, description="Who approved it, when the person had to"
    )
    model: str | None = Field(default=None, description="The model that dismissed it")
    probability: float | None = Field(
        default=None, description="The classifier's probability that raised the flag"
    )


class NotCountedPublic(BaseModel):
    """One group of an issue's "Not counted" list, newest first, a page at a time."""

    group: Literal["false_positives", "dismissed"]
    total: int
    rows: list[NotCountedRow] = Field(default_factory=list)
    next_offset: int | None = Field(
        default=None, description="Pass as `offset` for the next page; none at the end"
    )


class CountAgainRequest(BaseModel):
    """Undo false-positive marks and bring back flags the model dismissed."""

    finding_ids: list[uuid.UUID] = Field(
        default_factory=list, max_length=200, description="Marked findings to undo"
    )
    call_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=200,
        description="Calls whose dismissed flag on this issue's rule to bring back",
    )


class CountedAgainPublic(BaseModel):
    undone: int = Field(description="Marks undone")
    brought_back: int = Field(description="Dismissed flags that became findings")
