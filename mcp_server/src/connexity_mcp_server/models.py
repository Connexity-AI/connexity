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
    score: int | None = None
    score_change: int | None = None


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
    latency_p50: float | None = Field(
        default=None, description="p50 over every reply in the period, in seconds"
    )
    latency_p95: float | None = Field(
        default=None, description="p95 over every reply in the period, in seconds"
    )
    live_version: str | None = None
    live_since: datetime | None = None
    score: int | None = None
    score_change: int | None = None
    created_at: datetime


class ScoreMove(BaseModel):
    issue_id: str
    title: str
    points: float
    calls: int


class Score(BaseModel):
    """An agent's or a workspace's score for a period (none before onboarding is
    complete or without a checked call; `why_none` says which)."""

    score: int | None = None
    change: int | None = None
    previous: int | None = None
    period: str
    checked_calls: int = 0
    failed_calls: int = 0
    degraded_calls: int = 0
    moves: list[ScoreMove] = Field(default_factory=list)
    why_none: str | None = None


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


class IssueFindingOnCall(BaseModel):
    event_ids: list[str] = Field(default_factory=list)
    detail: dict[str, Any] | None = None
    effect: str
    check_version: int


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
    agent_version: str | None = Field(
        default=None, description="The agent version the call ran on"
    )
    # With an issue filter: that issue's findings on the call.
    issue_findings: list[IssueFindingOnCall] | None = None


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


class TaskRef(BaseModel):
    key: str
    title: str


class Task(BaseModel):
    key: str
    kind: str = Field(
        description=(
            "incident, issue_fix, onboarding, spec, clarifications, calls_to_review or "
            "tests"
        )
    )
    title: str
    position: int | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    facts: list[str] = Field(default_factory=list)
    waiting_for_person: bool = False
    blocks: list[TaskRef] = Field(default_factory=list)
    blocks_count: int = 0
    blocked_by: list[TaskRef] = Field(default_factory=list)
    blocked_by_count: int = 0


class EndedTask(BaseModel):
    title: str
    state: str = Field(description="done or returned")


class TaskCounts(BaseModel):
    to_do: int = 0
    waiting_for_person: int = 0
    in_progress_elsewhere: int = 0
    blocked: int = 0


class HeldTask(BaseModel):
    task: Task
    person: str
    assistant: str
    session: str = ""


class NextTask(BaseModel):
    task: Task | None = None
    previous: EndedTask | None = None
    waiting_for_person: list[Task] = Field(default_factory=list)
    counts: TaskCounts
    in_progress: list[HeldTask] = Field(default_factory=list)
    readiness_percent: int | None = None


ListWorkspacesResult = Answer[list[Workspace]]
AddAgentsResult = Answer[AddedAgents]
ConnectVoicePlatformResult = Answer[Connection]
GetReadinessResult = Answer[Readiness]


class DashboardStep(BaseModel):
    key: str
    label: str
    done: bool


class DashboardOnboarding(BaseModel):
    steps: list[DashboardStep] = Field(default_factory=list)
    areas_checked: int = 0
    areas_total: int = 0


class DashboardLatency(BaseModel):
    p50: float | None = None
    p95: float | None = None
    answers: int = 0


class DashboardDay(BaseModel):
    day: str
    calls: int
    failed: int
    degraded: int


class DashboardMark(BaseModel):
    day: str
    version: str
    agent_name: str


class DashboardArea(BaseModel):
    key: str
    name: str
    status: str
    waits_for: str | None = None
    failed: int = 0
    degraded: int = 0
    share: float | None = None
    top_issue_id: str | None = None
    top_issue_title: str | None = None


class Dashboard(BaseModel):
    """Where the workspace stands, for all agents or one, over the period."""

    period: str
    agent_id: str | None = None
    agents: list[dict[str, str]] = Field(default_factory=list)
    agents_counted: int = 0
    calls: int = 0
    onboarding: DashboardOnboarding | None = None
    score: Score | None = None
    failed: int = 0
    failed_share: float | None = None
    degraded: int = 0
    degraded_share: float | None = None
    latency: DashboardLatency | None = None
    days: list[DashboardDay] = Field(default_factory=list)
    marks: list[DashboardMark] = Field(default_factory=list)
    areas: list[DashboardArea] = Field(default_factory=list)


GetDashboardResult = Answer[Dashboard]
GetNextTaskResult = Answer[NextTask]


class TaskHolder(BaseModel):
    person: str
    assistant: str
    session: str = ""
    taken_at: str
    quiet_since: str | None = Field(
        default=None,
        description="When its session last asked for its next task, once over 30 "
        "minutes ago",
    )


class ListedTaskRef(BaseModel):
    key: str
    title: str
    state: str
    waiting_for_person: bool = False


class ListedTask(BaseModel):
    key: str
    kind: str
    title: str
    line: str
    severity: str | None = None
    position: int
    state: str = Field(
        description="in_progress, waiting (a question for the person) or to_do"
    )
    waiting_for_person: bool = False
    agent_id: str | None = None
    agent_name: str | None = None
    issue_id: str | None = None
    holder: TaskHolder | None = None
    blocks: list[ListedTaskRef] = Field(default_factory=list)
    blocked_by: list[ListedTaskRef] = Field(default_factory=list)


class DoneItem(BaseModel):
    title: str
    by: str
    at: str


class WorkingSession(BaseModel):
    person: str
    assistant: str
    session: str = ""
    task: str


class TaskList(BaseModel):
    tasks: list[ListedTask] = Field(default_factory=list)
    done: list[DoneItem] = Field(default_factory=list)
    sessions: list[WorkingSession] = Field(default_factory=list)
    waiting: int = 0
    total: int = 0


ListTasksResult = Answer[TaskList]
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


class IssueCheck(BaseModel):
    type: str
    title: str
    description: str
    kind: str
    version: int
    provider: str | None = None
    model: str | None = None
    needs: list[str] = Field(default_factory=list)
    detail_fields: dict[str, str] = Field(default_factory=dict)


class IssueSetting(BaseModel):
    mode: str
    default: str
    since: str | None = None


class IssueVersion(BaseModel):
    version: str | None = None
    calls: int


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
    check: IssueCheck | None = None
    setting: IssueSetting | None = None
    versions: list[IssueVersion] = Field(default_factory=list)
    live_version: str | None = None
    findings_all_time: int = 0
    calls_all_time: int = 0


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
    critical: bool = False
    scenarios: int = 0
    answered_by: str | None = None
    answered_at: str | None = None
    in_conflict: bool = False
    change: str | None = None


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


class SpecCounts(BaseModel):
    from_prompt: int = 0
    from_clarifications: int = 0
    in_conflict: int = 0
    critical: int = 0


class SpecComparison(BaseModel):
    version: int
    kept: int
    added: int
    dropped: int


class SpecChanges(BaseModel):
    rules: int
    kept: int
    added: int
    dropped: int
    carried: int = 0
    quotes_checked: bool


class Spec(BaseModel):
    agent_id: str
    agent_name: str
    current_agent_version: str | None = None
    state: str
    spec: SpecVersion | None = None
    latest_version: int | None = None
    groups: list[SpecGroup] = Field(default_factory=list)
    open_clarifications: int = 0
    counts: SpecCounts | None = None
    versions: list[SpecVersion] = Field(default_factory=list)
    comparison: SpecComparison | None = None
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
    critical: bool | None = Field(
        default=None,
        description=(
            "True when a failure of the rule must stop a release; left out, a kept "
            "rule keeps its mark and a new one is not critical"
        ),
    )


SpecResult = Answer[Spec]


class ClarificationAnswer(BaseModel):
    letter: str
    label: str
    rule: str


class ReplacedRule(BaseModel):
    key: str
    text: str | None = None


class Clarification(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    question: str
    answers: list[ClarificationAnswer] = Field(default_factory=list)
    category: str
    category_name: str
    touches: str | None = None
    calls_seen: int = 0
    call_ids: list[str] = Field(default_factory=list)
    spec_version: int | None = None
    replaces: ReplacedRule | None = None
    state: str
    raised_by: str
    raised_assistant: str | None = None
    raised_at: str
    answer: str | None = None
    answer_text: str | None = None
    answer_proposed: bool = False
    answer_spec_version: int | None = None
    decided_by: str | None = None
    decided_assistant: str | None = None
    decided_at: str | None = None


class ClarificationCounts(BaseModel):
    open: int = 0
    answered: int = 0
    parked: int = 0
    answered_this_week: int = 0


class Clarifications(BaseModel):
    counts: ClarificationCounts
    data: list[Clarification] = Field(default_factory=list)


class AnsweredSpec(BaseModel):
    agent_id: str
    agent_name: str
    spec_version: int
    rules_added: int


class ClarificationsAnswered(BaseModel):
    answered: int
    parked: int
    reopened: int = 0
    specs: list[AnsweredSpec] = Field(default_factory=list)
    open: int


class AnswerToRaise(BaseModel):
    """One answer of a question for `raise_clarifications`."""

    label: str = Field(description="What the person picks, e.g. 'Only when asked'")
    rule: str = Field(description="The spec rule this answer becomes, one sentence")


class QuestionToRaise(BaseModel):
    """One question for `raise_clarifications`."""

    question: str = Field(
        description="One plain sentence, with how often it happened"
    )
    answers: list[AnswerToRaise] = Field(description="Two to four, a to d")
    category: str = Field(description="A category key from `list_categories`")
    touches: str | None = Field(
        default=None, description="money, safety or compliance, when it protects one"
    )
    call_ids: list[str] | None = Field(
        default=None,
        description="The calls where it was seen, at most 50; none for a prompt change",
    )
    replaces_key: str | None = Field(
        default=None, description="The key of the spec rule the answer replaces"
    )


class AnswerToGive(BaseModel):
    """One decision for `answer_clarifications`."""

    clarification_id: str
    answer: str = Field(
        description="The letter the person chose (a to d), 'other' with text, 'park', "
        "or 'reopen' for a parked one"
    )
    text: str | None = Field(
        default=None,
        description="For 'other': the person's own answer, as the rule the agent "
        "should follow",
    )
    proposed: bool = Field(
        default=False,
        description="True when you proposed this answer and the person confirmed it; "
        "never for an answer they have not seen",
    )


RaiseClarificationsResult = Answer[list[Clarification]]
ListClarificationsResult = Answer[Clarifications]
AnswerClarificationsResult = Answer[ClarificationsAnswered]


class AgentSystem(BaseModel):
    kind: str
    name: str
    version: str | None = None


class AgentLatencyDay(BaseModel):
    day: str
    p50: float | None = Field(default=None, description="The day's p50, in seconds")
    replies: int = 0


class AgentVersionMark(BaseModel):
    day: str
    label: str


class AgentVersionOption(BaseModel):
    version: str
    calls: int = Field(description="Its calls, all time")
    live: bool = Field(default=False, description="The version of the latest call")


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
    latency_p50: float | None = None
    latency_p95: float | None = None
    latency_replies: int = Field(default=0, description="Replies the latency rests on")
    latency_days: list[AgentLatencyDay] = Field(default_factory=list)
    latency_peak: float | None = None
    version_marks: list[AgentVersionMark] = Field(default_factory=list)
    versions: list[AgentVersionOption] = Field(
        default_factory=list,
        description="Every agent version that has a call, the latest call's first",
    )
    version: str | None = Field(
        default=None, description="The version the numbers count; none for all"
    )
    version_days: list[str] = Field(
        default_factory=list, description="With a version: the period's days it ran"
    )
    score: Score | None = None


AgentResult = Answer[AgentPage]


class FakeToolResult(BaseModel):
    """A tool result the simulated call returns instead of calling the tool."""

    tool: str = Field(description="The tool's name, as the agent calls it")
    arguments: dict[str, Any] | None = Field(
        default=None,
        description="The arguments it answers (their keys must be present); leave out "
        "to answer any call of the tool",
    )
    result: dict[str, Any] | None = Field(
        default=None, description="What the tool returns, as JSON; invented values only"
    )


class ScenarioToWrite(BaseModel):
    """One scenario for `write_scenarios`: a stage for a simulated call."""

    id: str | None = Field(
        default=None, description="Only to replace or archive an existing scenario"
    )
    archive: bool = Field(
        default=False, description="True, with id, to archive it (it leaves its sets)"
    )
    name: str = ""
    description: str | None = Field(default=None, description="For people")
    caller: str | None = Field(default=None, description="Who the caller is")
    caller_goal: str | None = Field(
        default=None, description="What the caller wants from the call, in one line"
    )
    caller_behaviour: str | None = Field(
        default=None, description="How they behave: in a hurry, unsure, pushing back"
    )
    caller_knows: dict[str, Any] | None = Field(
        default=None, description="What the caller knows, such as their policy number"
    )
    agent_variables: dict[str, Any] | None = Field(
        default=None,
        description="The values the agent's platform passes in (dynamic variables)",
    )
    first_turn: str | None = Field(
        default=None, description="Who speaks first: agent or user (the default)"
    )
    first_message: str | None = Field(
        default=None, description="The first speaker's opening line"
    )
    fake_tool_results: list[FakeToolResult] = Field(default_factory=list)
    rules: list[str] = Field(
        default_factory=list,
        description="Keys from `get_spec` of the rules it expects to come up",
    )
    from_call_id: str | None = Field(
        default=None, description="A call of this agent the scenario was written from"
    )


class ScenarioRule(BaseModel):
    key: str
    text: str | None = None
    critical: bool = False
    gone: bool = False


class Scenario(BaseModel):
    id: str
    name: str
    description: str | None = None
    caller: str | None = None
    caller_goal: str | None = None
    caller_behaviour: str | None = None
    caller_knows: dict[str, Any] | None = None
    agent_variables: dict[str, Any] | None = None
    first_turn: str
    first_message: str | None = None
    fake_tool_results: list[FakeToolResult] = Field(default_factory=list)
    rules: list[ScenarioRule] = Field(default_factory=list)
    sets: list[str] = Field(default_factory=list)
    from_call_id: str | None = None
    updated_at: str


class ScenarioSet(BaseModel):
    id: str
    name: str
    description: str | None = None
    scenario_ids: list[str] = Field(default_factory=list)


class ScenarioCounts(BaseModel):
    scenarios: int = 0
    rules: int = 0
    rules_listed: int = 0
    critical_unlisted: int = 0
    listing_gone_rules: int = 0


class Scenarios(BaseModel):
    agent_id: str
    agent_name: str
    data: list[Scenario] = Field(default_factory=list)
    next_cursor: str | None = None
    sets: list[ScenarioSet] = Field(default_factory=list)
    counts: ScenarioCounts = Field(default_factory=ScenarioCounts)
    unlisted_rules: list[ScenarioRule] = Field(default_factory=list)


class WrittenScenarios(BaseModel):
    scenarios: list[Scenario] = Field(default_factory=list)
    archived: int = 0


WriteScenariosResult = Answer[WrittenScenarios]
ListScenariosResult = Answer[Scenarios]
ScenarioSetResult = Answer[ScenarioSet | None]



class StartedRun(BaseModel):
    run_id: str
    calls: int = Field(description="Simulated calls the run makes")


class RuleTotal(BaseModel):
    key: str
    text: str | None = None
    critical: bool = False
    passed: int = 0
    failed: int = 0
    did_not_come_up: int = 0
    flaky: bool = Field(
        default=False, description="It both passed and failed across repeats"
    )


class CheckTotal(BaseModel):
    check_type: str
    title: str
    found: int = Field(description="Simulated calls where it found something")
    critical: bool = Field(
        default=False, description="It fails calls, rather than only flagging them"
    )


class RuleVerdict(BaseModel):
    key: str
    outcome: str = Field(description="passed, failed or did_not_come_up")
    reason: str | None = None
    turns: list[int] = Field(default_factory=list)


class SimulatedFinding(BaseModel):
    check_type: str
    check_version: int
    kind: str
    mode: str
    key: str | None = None
    event_ids: list[str] = Field(default_factory=list)
    detail: dict[str, Any] | None = None


class SimulatedCall(BaseModel):
    id: str
    scenario_id: str
    scenario_name: str
    repeat: int = Field(description="Which repeat, from 1")
    finished: bool
    error: str | None = None
    turns: int | None = None
    verdicts: list[RuleVerdict] = Field(default_factory=list)
    findings: list[SimulatedFinding] = Field(default_factory=list)
    default_fakes: list[str] = Field(
        default_factory=list,
        description="Tools no scenario fake answered; they got the default fake",
    )
    cost_usd: float | None = None
    url: str | None = Field(
        default=None, description="The simulated call in the app; give it to the person"
    )


class TestRunCounts(BaseModel):
    calls: int = 0
    finished: int = 0
    errors: int = 0
    rules_failed: int = 0
    critical_failed: int = 0
    flaky: int = 0
    findings: int = 0


class RunTotals(BaseModel):
    rules: int = Field(description="Rules in the run's spec")
    passed: int = 0
    failed: int = 0
    did_not_come_up: int = 0
    no_scenario: int = Field(default=0, description="Rules no scenario of the run lists")
    not_judged: int = Field(
        default=0, description="Rules only calls that stopped listed; in no column"
    )
    critical: int = Field(
        default=0,
        description="Critical rules that failed and critical code checks that found "
        "something",
    )
    stopped: int = Field(default=0, description="Simulated calls that ended in an error")
    judged_calls: int = Field(
        default=0, description="Simulated calls a judge read; none means no result"
    )


class TestRun(BaseModel):
    id: str
    status: str = Field(description="pending, running, completed or failed")
    status_detail: str | None = None
    scope: str = Field(description="set, pick or all")
    set_name: str | None = None
    repeats: int
    spec_version: int | None = None
    platform_version: str | None = Field(
        default=None, description="The agent's version tested; none for the latest"
    )
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    counts: TestRunCounts = Field(default_factory=TestRunCounts)
    cost_usd: float | None = None
    full: bool = Field(
        default=False, description="A run of every scenario: only it decides the verdict"
    )
    verdict: str | None = Field(
        default=None,
        description="A completed full run's verdict: verified, failed, partial or "
        "not_verified",
    )
    result: str | None = Field(
        default=None, description="A completed on-demand run's result: passed or failed"
    )
    totals: RunTotals | None = Field(
        default=None, description="Rules by outcome, each counted once per run"
    )
    ran_by: str | None = Field(default=None, description="The person")
    assistant_name: str | None = None
    session_name: str | None = None


class TestRunDetail(TestRun):
    rules: list[RuleTotal] = Field(
        default_factory=list, description="Failed rules first, critical first"
    )
    dropped_rules: list[str] = Field(default_factory=list)
    checks: list[CheckTotal] = Field(default_factory=list)
    calls: list[SimulatedCall] = Field(default_factory=list)


class UncheckedRule(BaseModel):
    key: str
    text: str
    category: str
    critical: bool = False
    why: str = Field(description="no_scenario, did_not_come_up or not_judged")


class Coverage(BaseModel):
    rules: int = Field(description="Rules in the agent's latest spec")
    covered: int = Field(description="Rules at least one active scenario lists")
    pct: int
    uncovered: list[UncheckedRule] = Field(
        default_factory=list, description="Rules no scenario lists"
    )


class StoppedCalls(BaseModel):
    calls: int = Field(description="Simulated calls that ended in an error")
    reason: str = Field(description="The most common error, in plain words")
    run_id: str = Field(description="A run with one of those calls")


class VerifiedVersion(BaseModel):
    version: str
    at: str = Field(description="When its full run completed")


class SameContent(BaseModel):
    version: str = Field(description="The version number its full run tested")
    run_id: str
    at: str = Field(description="When that full run completed")


class LiveVersion(BaseModel):
    version: str
    verdict: str = Field(description="From the live version's latest full run")
    at: str | None = Field(default=None, description="When that full run completed")


class VersionResults(BaseModel):
    version: str | None = Field(
        default=None, description="The newest tested version, live or not, or the one asked"
    )
    edited_since: str | None = Field(
        default=None,
        description="When its last full run ran, if the version was edited after it",
    )
    same_content: SameContent | None = Field(
        default=None,
        description="The other version whose full run of the same content decided",
    )
    live_version: str | None = None
    live: LiveVersion | None = Field(
        default=None, description="The live version's state, when it is not the one shown"
    )
    verdict: str = Field(
        description="From the latest full run: verified, failed, partial or not_verified"
    )
    full_run: TestRun | None = Field(
        default=None, description="The full run that decided the verdict"
    )
    last_verified: VerifiedVersion | None = Field(
        default=None, description="The newest other version a full run verified"
    )
    critical_failed: list[str] = Field(default_factory=list)
    critical_checks: list[str] = Field(default_factory=list)
    rules: list[RuleTotal] = Field(default_factory=list)
    checks: list[CheckTotal] = Field(default_factory=list)
    unchecked: list[UncheckedRule] = Field(
        default_factory=list, description="Rules the full run did not check"
    )
    runs: list[TestRun] = Field(default_factory=list)
    coverage: Coverage | None = Field(
        default=None, description="Tests written: the latest spec's rules with a scenario"
    )
    stopped: StoppedCalls | None = Field(
        default=None,
        description="The full run's simulated calls that ended in an error",
    )


class TestRuns(BaseModel):
    run: TestRunDetail | None = None
    results: VersionResults | None = Field(
        default=None,
        description="Without a run id: the tested version's results across its runs",
    )
    runs: list[TestRun] = Field(default_factory=list)


RunScenariosResult = Answer[StartedRun]
TestRunsResult = Answer[TestRuns]


class FeedbackSent(BaseModel):
    report_id: str = Field(description="Give it to the person if they ask")


SendFeedbackResult = Answer[FeedbackSent]
