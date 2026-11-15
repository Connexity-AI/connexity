from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Answer(BaseModel, Generic[T]):
    """The standard answer of every Connexity tool."""

    data: T = Field(description="The facts: the result of the call")
    rules: list[str] = Field(
        default_factory=list,
        description="The rules that apply to what was returned. Follow them.",
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="What you can do next, in order, naming the tool to call",
    )
    guide: str = Field(description="URI of the guide for this part of Connexity")
    next_cursor: str | None = Field(
        default=None,
        description="On lists: pass as `cursor` for the next page; empty on the last",
    )


class Workspace(BaseModel):
    id: str
    name: str


class Agent(BaseModel):
    id: str
    name: str
    platform: str | None = None
    platform_agent_id: str | None = None
    platform_agent_name: str | None = None
    spec: str | None = None
    spec_version: int | None = None
    type: str | None = None
    calls: int | None = None
    latency_seconds: float | None = None
    created_at: datetime


class ReadinessStep(BaseModel):
    key: str
    name: str
    state: str = Field(description="done, in_progress or not_started")
    detail: str | None = None


class Readiness(BaseModel):
    steps: list[ReadinessStep]
    done: int
    total: int
    percent: int
    first_scan_done: bool
    mcp_url: str | None = None


class Connection(BaseModel):
    platform: str
    masked_api_key: str
    replaced_earlier_key: bool
    connected_by: str | None = None


class AgentToAdd(BaseModel):
    platform_agent_id: str = Field(description="The agent's id in Retell")
    name: str | None = Field(
        default=None, description="Defaults to the agent's name in Retell"
    )


class RefusedAgent(BaseModel):
    platform_agent_id: str
    reason: str


class AddedAgents(BaseModel):
    added: list[Agent] = Field(default_factory=list)
    already_added: list[Agent] = Field(default_factory=list)
    refused: list[RefusedAgent] = Field(default_factory=list)


class AgentScan(BaseModel):
    agent_id: str
    name: str
    stored: int
    total: int | None = None
    finished: bool


class ScanProgress(BaseModel):
    agents: list[AgentScan] = Field(default_factory=list)
    stored_this_step: int
    finished: bool
    calls_without_versions: int = 0


class WorstFinding(BaseModel):
    title: str
    key: str | None = None
    category: str
    severity: str
    found_by: str


class IssueMoment(BaseModel):
    at_seconds: float
    times: int


class CallItem(BaseModel):
    id: str
    started_at: str
    agent_id: str
    agent_name: str
    caller_last_four: str | None = None
    duration_seconds: int | None = None
    result: str
    worst_finding: WorstFinding | None = None
    moment: IssueMoment | None = None


class CallTiles(BaseModel):
    calls: int
    failed: int
    degraded: int
    clean: int
    unchecked: int


class Calls(BaseModel):
    tiles: CallTiles
    calls: list[CallItem] = Field(default_factory=list)


class KeyValue(BaseModel):
    key: str
    value: str


class CallEntry(BaseModel):
    kind: str
    at_seconds: float
    end_seconds: float | None = None
    speaker: str | None = None
    text: str | None = None
    tool: str | None = None
    status: str | None = None
    duration_ms: int | None = None
    arguments: list[KeyValue] = Field(default_factory=list)
    result: list[KeyValue] = Field(default_factory=list)
    workflow: str | None = None
    finding_ids: list[str] = Field(default_factory=list)


class CallFinding(BaseModel):
    id: str
    at_seconds: float
    text: str
    category: str
    severity: str
    found_by: str
    entry_index: int | None = None


class CallDetail(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    started_at: str
    duration_seconds: int | None = None
    caller_last_four: str | None = None
    result: str
    version: str | None = None
    has_recording: bool
    entries: list[CallEntry] = Field(default_factory=list)
    findings: list[CallFinding] = Field(default_factory=list)


class Issue(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    title: str
    check_type: str
    key: str | None = None
    category: str
    severity: str
    found_by: str
    state: str
    resolved_version: str | None = None
    calls_affected: int
    calls_total: int
    last_seen_at: str | None = None


class IssueTiles(BaseModel):
    open: int
    critical: int
    reopened: int
    resolved: int
    calls_affected: int
    calls: int


class Issues(BaseModel):
    tiles: IssueTiles
    issues: list[Issue] = Field(default_factory=list)


class Category(BaseModel):
    key: str
    name: str
    position: int
    kind: str


ListWorkspacesResult = Answer[list[Workspace]]
AddAgentsResult = Answer[AddedAgents]
ConnectVoicePlatformResult = Answer[Connection]
GetReadinessResult = Answer[Readiness]
CreateWorkspaceResult = Answer[Workspace]
ListAgentsResult = Answer[list[Agent]]
ScanCallsResult = Answer[ScanProgress]
ListCategoriesResult = Answer[list[Category]]
class IssueArchive(BaseModel):
    by: str
    assistant: str | None = None
    at: str
    duration: str
    reason: str | None = None


class IssuePageTiles(BaseModel):
    calls_affected: int
    calls_total: int
    first_seen_at: str | None = None
    last_seen_at: str | None = None


class IssueFound(BaseModel):
    at: str
    call_id: str
    caller_last_four: str | None = None


class IssueFixed(BaseModel):
    version: str | None = None
    at: str


class IssueChain(BaseModel):
    found: IssueFound | None = None
    fixed: IssueFixed | None = None


class IssueDay(BaseModel):
    day: str
    calls: int


class IssueMark(BaseModel):
    day: str
    kind: str
    label: str


class IssueAffectedCall(BaseModel):
    call_id: str
    started_at: str
    caller_last_four: str | None = None
    duration_seconds: int | None = None
    result: str
    moment: IssueMoment


class IssueHistoryLine(BaseModel):
    kind: str
    what: str
    by: str | None = None
    assistant: str | None = None
    at: str
    reason: str | None = None
    duration: str | None = None


class IssuePage(BaseModel):
    id: str
    title: str
    check_type: str
    key: str | None = None
    agent_id: str
    agent_name: str
    category: dict[str, str]
    severity: str
    found_by: str
    state: str
    resolved_version: str | None = None
    archive: IssueArchive | None = None
    tiles: IssuePageTiles
    chain: IssueChain
    days: list[IssueDay] = Field(default_factory=list)
    marks: list[IssueMark] = Field(default_factory=list)
    peak: int = 0
    affected_calls: list[IssueAffectedCall] = Field(default_factory=list)
    history: list[IssueHistoryLine] = Field(default_factory=list)


ListIssuesResult = Answer[Issues]
IssueResult = Answer[IssuePage]
ListCallsResult = Answer[Calls]
GetCallResult = Answer[CallDetail]


class SpecRule(BaseModel):
    key: str
    text: str
    source: str
    quote: str | None = None
    touches: str | None = None


class SpecGroup(BaseModel):
    category: str
    name: str
    rules: list[SpecRule] = Field(default_factory=list)


class SpecVersion(BaseModel):
    version: int
    agent_version: str
    origin: str
    written_by: str | None = None
    assistant: str | None = None
    created_at: str
    rule_count: int


class SpecPrompt(BaseModel):
    kind: str
    version: str
    content: Any = None


class SpecChanges(BaseModel):
    rules: int
    kept: int
    added: int
    dropped: int
    quotes_checked: bool


class Spec(BaseModel):
    agent_id: str
    agent_name: str
    current_agent_version: str | None = None
    state: str
    spec: SpecVersion | None = None
    latest_version: int | None = None
    groups: list[SpecGroup] = Field(default_factory=list)
    prompt: SpecPrompt | None = None
    changes: SpecChanges | None = None


class SpecRuleToWrite(BaseModel):
    """One rule for `write_spec`."""

    text: str = Field(description="The rule in one plain sentence")
    category: str = Field(description="A category key from `list_categories`")
    quote: str = Field(description="The prompt's words the rule rests on, exactly")
    touches: str | None = Field(
        default=None, description="money, safety or compliance, when it protects one"
    )
    key: str | None = Field(
        default=None, description="Only for a rule kept from the previous version"
    )


SpecResult = Answer[Spec]


class AgentSystem(BaseModel):
    kind: str
    name: str
    version: str | None = None


class AgentLatencyDay(BaseModel):
    day: str
    seconds: float | None = None
    calls: int = 0


class AgentVersionMark(BaseModel):
    day: str
    label: str


class AgentPage(BaseModel):
    id: str
    name: str
    platform: str | None = None
    type: str | None = None
    live_version: str | None = None
    live_since: str | None = None
    model: str | None = None
    systems: list[AgentSystem] = Field(default_factory=list)
    spec: str
    period: str
    calls: int
    latency_seconds: float | None = None
    latency_calls: int = 0
    latency_days: list[AgentLatencyDay] = Field(default_factory=list)
    latency_peak: float | None = None
    version_marks: list[AgentVersionMark] = Field(default_factory=list)


AgentResult = Answer[AgentPage]
