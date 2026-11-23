"""What the backend's `/mcp` routes answer: the standard shape every MCP tool returns.

Every answer carries the facts (`data`), the rules that apply to them, numbered next
steps naming the tool to call, and a link to the guide for this part of Connexity.
Lists add `next_cursor`. Errors carry a message, next steps and a guide in the same way
(see `McpErrorDetail`).
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, JsonValue, StringConstraints

from app.models.agency import AgencyRole
from app.models.agent_list import AgentType
from app.models.agent_page import AgentPagePublic
from app.models.call_list import CallListItemPublic, CallTilesPublic
from app.models.enums import (
    AssistantTaskState,
    CheckKind,
    CheckMode,
    FeedbackKind,
    FindingEffect,
    FirstTurn,
    Platform,
    SpecRuleTouches,
    TaskKind,
)
from app.models.issue_list import IssueListItemPublic, IssueTilesPublic
from app.models.issue_page import IssuePagePublic
from app.models.scenario import ScenarioPublic
from app.models.score import ScorePublic
from app.models.spec import SpecState
from app.models.test_run import (
    RunStatusPublic,
    TestRunDetailPublic,
    TestRunPublic,
    VersionResultsPublic,
)
from app.models.work import WorkDonePublic, WorkSessionPublic, WorkTaskPublic

T = TypeVar("T")

GUIDE_GETTING_STARTED = "connexity://guides/getting-started"
GUIDE_WORKSPACES = "connexity://guides/workspaces"
GUIDE_READINESS = "connexity://guides/readiness"
GUIDE_CONNECT = "connexity://guides/connect"
GUIDE_CATEGORIES = "connexity://guides/categories"
GUIDE_ISSUES = "connexity://guides/issues"
GUIDE_SPEC = "connexity://guides/spec"
GUIDE_CALLS = "connexity://guides/calls"
GUIDE_SCENARIOS = "connexity://guides/scenarios"
GUIDE_FEEDBACK = "connexity://guides/feedback"
GUIDE_USAGE = "connexity://guides/usage"
GUIDE_PEOPLE = "connexity://guides/people"


class McpAnswer(BaseModel, Generic[T]):
    data: T = Field(description="The facts: the result of the call")
    rules: list[str] = Field(
        default_factory=list,
        description="The rules that apply to what was returned, one sentence each",
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="Steps the assistant can take next, in order, naming the tool",
    )
    guide: str = Field(description="The guide for this part of Connexity")
    next_cursor: str | None = Field(
        default=None,
        description="On lists: pass as `cursor` for the next page; empty on the last",
    )


class McpErrorDetail(BaseModel):
    """The `detail` of an error answered by an `/mcp` route."""

    error: str
    next_steps: list[str] = Field(default_factory=list)
    guide: str = GUIDE_GETTING_STARTED


class McpAgencyRef(BaseModel):
    id: uuid.UUID
    name: str


class McpWorkspace(BaseModel):
    id: uuid.UUID
    name: str
    agency: McpAgencyRef = Field(
        description="The agency the workspace belongs to; one agency has a workspace "
        "per client"
    )
    role: AgencyRole = Field(
        description="The person's role in that agency: an admin manages people and "
        "billing and creates workspaces; a member works in their workspaces"
    )
    can_approve: bool = Field(
        description="Whether the person may make the critical decisions in this "
        "workspace"
    )
    score: int | None = Field(
        default=None,
        description="0 to 100 over the last 30 days; none before onboarding is "
        "complete or with no checked call",
    )
    score_change: int | None = Field(
        default=None, description="Against the 30 days before"
    )


class McpAgent(BaseModel):
    id: uuid.UUID
    name: str
    platform: Platform | None = None
    platform_agent_id: str | None = Field(
        default=None, description="The agent's id on its voice platform (Retell)"
    )
    platform_agent_name: str | None = None
    created_at: datetime
    spec: SpecState | None = Field(
        default=None,
        description="none, current, or needs_review (adopted, or behind the agent)",
    )
    spec_version: int | None = Field(
        default=None, description="Its latest spec version"
    )
    type: AgentType | None = Field(
        default=None, description="single_prompt or conversational_flow, when known"
    )
    score: int | None = Field(
        default=None,
        description="0 to 100 for the period; none before onboarding is complete or "
        "with no checked call",
    )
    score_change: int | None = Field(
        default=None, description="Against the previous period of the same length"
    )
    calls: int | None = Field(default=None, description="Calls in the period")
    critical_issues: int = Field(
        default=0,
        description="Open or reopened critical issues that showed in the period",
    )
    latency_p50: float | None = Field(
        default=None, description="p50 over every reply in the period, in seconds"
    )
    latency_p95: float | None = Field(
        default=None, description="p95 over every reply in the period, in seconds"
    )
    live_version: str | None = Field(
        default=None, description="The agent version of its most recent call"
    )
    live_since: datetime | None = Field(
        default=None, description="When the first call on that version started"
    )


class McpVoicePlatform(StrEnum):
    RETELL = "retell"
    VAPI = "vapi"
    ELEVENLABS = "elevenlabs"


class McpConnectVoicePlatform(BaseModel):
    platform: McpVoicePlatform = McpVoicePlatform.RETELL
    api_key: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)
    ]


class McpConnection(BaseModel):
    platform: str
    masked_api_key: str
    replaced_earlier_key: bool
    connected_by: str | None = Field(
        default=None, description="The person, and the assistant, who connected it"
    )


class McpAgentToAdd(BaseModel):
    platform_agent_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    name: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=255)
    ] = Field(default=None, description="Defaults to the agent's name on the platform")


class McpAddAgents(BaseModel):
    agents: list[McpAgentToAdd] = Field(min_length=1, max_length=100)


class McpRefusedAgent(BaseModel):
    platform_agent_id: str
    reason: str


class McpAddedAgents(BaseModel):
    added: list[McpAgent]
    already_added: list[McpAgent]
    refused: list[McpRefusedAgent]


class McpAgentScan(BaseModel):
    agent_id: uuid.UUID
    name: str
    stored: int = Field(description="Calls stored from the agent's scan window")
    total: int | None = Field(
        description="Finished calls Retell listed in the window; empty until listed"
    )
    finished: bool


class McpScanProgress(BaseModel):
    agents: list[McpAgentScan]
    stored_this_step: int
    finished: bool = Field(description="Every added agent's first scan has finished")
    calls_without_versions: int = Field(
        description="Stored calls whose agent version could not be resolved"
    )


class McpSpecRule(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
    category: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=64)
    ] = Field(description="A category key from `list_categories`")
    quote: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=4000)
    ] = Field(default=None, description="The prompt's words the rule rests on")
    touches: SpecRuleTouches | None = Field(
        default=None, description="money, safety or compliance, when it protects one"
    )
    key: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=64)
    ] = Field(
        default=None, description="Only for a rule kept from the previous version"
    )
    critical: bool | None = Field(
        default=None,
        description=(
            "True when a failure of the rule must stop a release; left out, a kept "
            "rule keeps its mark and a new one is not critical"
        ),
    )


class McpWriteSpec(BaseModel):
    rules: list[McpSpecRule] = Field(max_length=1000)


type RuleKey = Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)]


class McpMarkCritical(BaseModel):
    critical: list[RuleKey] = Field(
        default_factory=list,
        max_length=500,
        description="Keys of rules whose failure must stop a release",
    )
    not_critical: list[RuleKey] = Field(
        default_factory=list,
        max_length=500,
        description="Keys of rules whose failure is a Warning",
    )


type ShortText = Annotated[str, StringConstraints(max_length=4000)]


class McpFakeToolResult(BaseModel):
    tool: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] = (
        Field(description="The tool's name, as the agent calls it")
    )
    arguments: dict[str, Any] | None = Field(
        default=None,
        description="The arguments it answers (their keys must be present); leave out "
        "to answer any call of the tool",
    )
    result: dict[str, Any] | None = Field(
        default=None, description="What the tool returns, as JSON; invented values only"
    )


class McpScenario(BaseModel):
    id: uuid.UUID | None = Field(
        default=None, description="Only to replace or archive an existing scenario"
    )
    archive: bool = Field(
        default=False, description="True, with id, to archive it (it leaves its sets)"
    )
    name: Annotated[str, StringConstraints(max_length=255)] = ""
    description: ShortText | None = Field(default=None, description="For people")
    caller: ShortText | None = Field(default=None, description="Who the caller is")
    caller_goal: ShortText | None = Field(
        default=None, description="What the caller wants from the call, in one line"
    )
    caller_behaviour: ShortText | None = Field(
        default=None, description="How they behave: in a hurry, unsure, pushing back"
    )
    caller_knows: dict[str, Any] | None = Field(
        default=None, description="What the caller knows, such as their policy number"
    )
    agent_variables: dict[str, Any] | None = Field(
        default=None,
        description="The values the agent's platform passes in (dynamic variables)",
    )
    first_turn: FirstTurn = Field(
        default=FirstTurn.USER, description="Who speaks first: agent or user"
    )
    first_message: ShortText | None = Field(
        default=None, description="The first speaker's opening line"
    )
    fake_tool_results: list[McpFakeToolResult] = Field(
        default_factory=list, max_length=50
    )
    rules: list[Annotated[str, StringConstraints(max_length=64)]] = Field(
        default_factory=list,
        max_length=50,
        description="Keys from `get_spec` of the rules it expects to come up",
    )
    from_call_id: uuid.UUID | None = Field(
        default=None, description="A call of this agent the scenario was written from"
    )


class McpWriteScenarios(BaseModel):
    scenarios: list[McpScenario] = Field(max_length=100)


class McpWriteScenarioSet(BaseModel):
    name: Annotated[str, StringConstraints(max_length=255)]
    scenario_ids: list[uuid.UUID] = Field(
        max_length=500, description="In order; empty archives the set"
    )
    description: ShortText | None = None


class McpWrittenScenarios(BaseModel):
    scenarios: list[ScenarioPublic]
    archived: int


class McpRunScenarios(BaseModel):
    """Exactly one of ``set``, ``scenario_ids`` or ``all``."""

    set: Annotated[str, StringConstraints(max_length=255)] | None = Field(
        default=None, description="Run this named set"
    )
    scenario_ids: list[uuid.UUID] | None = Field(
        default=None, max_length=200, description="Run this pick of scenarios"
    )
    all: bool = Field(default=False, description="Run every active scenario")
    repeats: int = Field(
        default=3, ge=1, le=5, description="How many times each scenario runs"
    )
    version: int | None = Field(
        default=None,
        ge=0,
        description="The agent's version on its platform; none for the latest",
    )
    session: Annotated[str, StringConstraints(max_length=40)] | None = Field(
        default=None,
        description="This session's name, the same on every call in it; shown with the "
        "run",
    )


class McpRunCost(BaseModel):
    """What an earlier run of the same scenarios came to, at list price."""

    run_id: uuid.UUID
    caller_messages: int
    cost_usd: float


class McpStartedRun(BaseModel):
    run_id: uuid.UUID
    calls: int = Field(description="Simulated calls the run makes")
    price_per_caller_message_usd: float = Field(
        description="List price of each message the simulated caller sends"
    )
    last_run: McpRunCost | None = Field(
        default=None,
        description="The last completed run of the same set, or of every scenario",
    )


class McpTestRuns(BaseModel):
    """One run in detail when ``run_id`` was given; otherwise a tested version's
    results and the agent's runs."""

    run: TestRunDetailPublic | None = None
    status: RunStatusPublic | None = Field(
        default=None, description="With `status_only`: the run's status alone"
    )
    results: VersionResultsPublic | None = Field(
        default=None,
        description="Without a run id: the version's verdict from its latest full run, "
        "and its runs",
    )
    runs: list[TestRunPublic] = Field(default_factory=list)


class McpClarificationAnswer(BaseModel):
    label: Annotated[str, StringConstraints(max_length=2000)] = Field(
        description="A short answer the person picks, e.g. 'Only when the caller asks'"
    )
    rule: Annotated[str, StringConstraints(max_length=2000)] = Field(
        description="The spec rule this answer becomes, in one plain sentence"
    )


class McpClarificationQuestion(BaseModel):
    question: Annotated[str, StringConstraints(max_length=2000)] = Field(
        description="One plain sentence, with how often it happened"
    )
    answers: list[McpClarificationAnswer] = Field(
        max_length=10, description="Two to four, a to d"
    )
    category: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=64)
    ] = Field(description="A category key from `list_categories`")
    touches: SpecRuleTouches | None = Field(
        default=None, description="money, safety or compliance, when it protects one"
    )
    call_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=200,
        description="The calls where it was seen, at most 50; none for a prompt change",
    )
    replaces_key: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=64)
    ] = Field(default=None, description="The key of the spec rule the answer replaces")


class McpRaiseClarifications(BaseModel):
    questions: list[McpClarificationQuestion] = Field(max_length=100)


class McpClarificationDecision(BaseModel):
    clarification_id: uuid.UUID
    answer: Annotated[str, StringConstraints(max_length=16)] = Field(
        description="The letter the person chose (a to d), 'other' with text, 'park', "
        "or 'reopen' for a parked one"
    )
    text: Annotated[str | None, StringConstraints(max_length=500)] = Field(
        default=None,
        description="For 'other': the person's own answer, as the rule the agent "
        "should follow",
    )
    proposed: bool = Field(
        default=False,
        description="True when you proposed this answer and the person confirmed it; "
        "never for an answer they have not seen",
    )


class McpAgentPage(AgentPagePublic):
    score: ScorePublic | None = Field(
        default=None,
        description="The agent's score for the period, its change and what moves it",
    )


class McpAnswerClarifications(BaseModel):
    answers: list[McpClarificationDecision] = Field(max_length=50)


class McpArchiveIssue(BaseModel):
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ] = Field(description="Why, in the person's own words")
    duration: Literal["until_spike", "forever"] = "until_spike"


class McpIssueCheck(BaseModel):
    """The check that finds the issue, as the registry has it now."""

    type: str
    title: str
    description: str
    kind: CheckKind = Field(description="code_based, classifier or judge")
    version: int = Field(description="The check's current version")
    provider: str | None = Field(
        default=None, description="For a model check: who runs the model"
    )
    model: str | None = Field(
        default=None, description="For a model check: the pinned model"
    )
    needs: list[str] = Field(
        description="What a call's trace must have for the check to run on it"
    )
    detail_fields: dict[str, str] = Field(
        description="What each key of a finding's detail means"
    )


class McpIssueSetting(BaseModel):
    mode: CheckMode = Field(description="What the check does for this agent now")
    default: CheckMode = Field(description="The issue type's default")
    since: datetime | None = Field(
        default=None, description="When a person last changed it; none if never"
    )


class McpIssueVersion(BaseModel):
    version: str | None = Field(description="The agent version; none if unreported")
    calls: int = Field(description="Calls on it the issue was found on, last 30 days")


class McpIssueSinceVersion(BaseModel):
    """The agent's real calls since a version went live, and this issue among them.
    A call counts when it ran that version or a later one."""

    version: str = Field(description="The version counted from")
    is_fix: bool = Field(description="Whether it is the version the issue is fixed in")
    live_at: datetime | None = Field(
        default=None,
        description="When its first real call started; none if it served none yet",
    )
    calls: int = Field(description="The agent's real calls on it or a later version")
    calls_with_issue: int = Field(description="How many of those have this issue")
    last_call_id: uuid.UUID | None = Field(
        default=None, description="The newest of those with this issue"
    )
    last_call_at: datetime | None = Field(
        default=None, description="When that call started"
    )


class McpIssue(IssuePagePublic):
    """Everything Connexity has about one issue. The calls themselves come from
    `list_calls` with the issue's id."""

    check: McpIssueCheck | None = Field(
        default=None, description="None when the check has since been removed"
    )
    setting: McpIssueSetting | None = None
    versions: list[McpIssueVersion] = Field(
        description="Affected calls per agent version, last 30 days, most first"
    )
    live_version: str | None = Field(
        default=None, description="The agent version on the agent's newest call"
    )
    since_version: McpIssueSinceVersion | None = Field(
        default=None,
        description="What happened since the fix's version went live, or since the "
        "version asked for with `since_version`; none when there is neither",
    )
    findings_all_time: int = Field(description="Findings of this issue, ever")
    calls_all_time: int = Field(description="Calls it was found on, ever")


class McpMarkFixed(BaseModel):
    version: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ] = Field(description="The agent's version on its platform that carries the fix")
    note: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=2000)
    ] = Field(default=None, description="What was changed, in a sentence")


class McpUnarchiveIssue(BaseModel):
    reason: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=2000)
    ] = None


class McpIssues(BaseModel):
    tiles: IssueTilesPublic = Field(description="Counts for the agent and period")
    issues: list[IssueListItemPublic] = Field(description="Worst first")


class McpIssueFinding(BaseModel):
    """One finding of the filtered issue on a call."""

    event_ids: list[str] = Field(
        description="The call's timeline events it points at; `get_call` shows them"
    )
    detail: dict[str, JsonValue] | None = Field(
        default=None,
        description="What the check recorded; `get_issue` says what each key means",
    )
    effect: FindingEffect = Field(description="flags, or fails the call")
    check_version: int


class McpCallItem(CallListItemPublic):
    issue_findings: list[McpIssueFinding] | None = Field(
        default=None, description="With issue_id: that issue's findings on the call"
    )


class McpCalls(BaseModel):
    tiles: CallTilesPublic = Field(description="Counts for the filters and period")
    calls: list[McpCallItem]


class McpTaskRef(BaseModel):
    key: str
    title: str


class McpTask(BaseModel):
    key: str = Field(
        description="Stays the same while the task exists: spec:<agent id>"
    )
    kind: TaskKind
    title: str = Field(description="The task in one plain sentence")
    position: int | None = Field(
        default=None, description="Its place in the workspace's list, 1 at the top"
    )
    agent_id: uuid.UUID | None = None
    agent_name: str | None = None
    facts: list[str] = Field(description="Short facts: counts, versions, the size")
    waiting_for_person: bool = Field(
        default=False, description="The next move is the person's, not yours"
    )
    blocks: list[McpTaskRef] = Field(
        default_factory=list, description="Tasks that wait for this one (up to 5)"
    )
    blocks_count: int = 0
    blocked_by: list[McpTaskRef] = Field(
        default_factory=list,
        description="Tasks this one waits for (up to 5); never handed out until done",
    )
    blocked_by_count: int = 0


class McpEndedTask(BaseModel):
    title: str
    state: AssistantTaskState = Field(
        description=(
            "done; waiting (your part is done, the rest is the person's); returned "
            "(back in the list, its work still there)"
        )
    )


class McpTaskCounts(BaseModel):
    to_do: int = Field(description="Tasks after this one that an assistant can take")
    waiting_for_person: int
    in_progress_elsewhere: int = Field(
        description="Tasks other assistants are working on"
    )
    blocked: int = Field(
        default=0, description="Tasks that wait for the tasks under their Blocked by"
    )


class McpHeldTask(BaseModel):
    task: McpTask
    person: str = Field(description="Whose assistant holds it")
    assistant: str
    session: str = Field(description="The session's name; empty when it gave none")


class McpNextTask(BaseModel):
    task: McpTask | None = Field(
        default=None, description="Yours now; None when nothing waits for you"
    )
    previous: McpEndedTask | None = Field(
        default=None, description="Your previous task, ended by asking for this one"
    )
    waiting_for_person: list[McpTask] = Field(
        description="Tasks only the person can move on, top first (up to 10)"
    )
    counts: McpTaskCounts
    in_progress: list[McpHeldTask] = Field(
        default_factory=list,
        description="Tasks other sessions are working on, top first (up to 10)",
    )
    readiness_percent: int | None = Field(
        default=None, description="Setup completeness, when nothing waits for you"
    )


class McpTaskList(BaseModel):
    tasks: list[WorkTaskPublic] = Field(
        description="This page of the list, in Connexity's order, each with its state"
    )
    done: list[WorkDonePublic] = Field(description="The last 7 days, newest first")
    sessions: list[WorkSessionPublic] = Field(description="Sessions working now")
    waiting: int = Field(description="Tasks waiting for the person")
    total: int = Field(description="Tasks in the whole list")


class McpSendFeedback(BaseModel):
    """A bug in Connexity, or something it cannot do that the work needs."""

    kind: FeedbackKind = Field(description="bug or feature_request")
    title: Annotated[str, StringConstraints(max_length=200)] = Field(
        description="One line: what is wrong or missing"
    )
    what_happened: Annotated[str, StringConstraints(max_length=4000)] | None = Field(
        default=None,
        description="For a bug: what you did, which tool, what you expected and what "
        "came back",
    )
    wanted: Annotated[str, StringConstraints(max_length=4000)] | None = Field(
        default=None,
        description="For a feature request: what the work needed and could not do",
    )
    tool: Annotated[str, StringConstraints(max_length=100)] | None = Field(
        default=None, description="The Connexity tool involved"
    )
    error: str | None = Field(
        default=None,
        description="The answer's error text; long text is cut, not refused",
    )
    ids: list[Annotated[str, StringConstraints(max_length=100)]] = Field(
        default_factory=list,
        max_length=50,
        description="The call, issue, run, agent or task ids involved",
    )
    session: Annotated[str, StringConstraints(max_length=40)] | None = Field(
        default=None, description="This session's name, as on `get_next_task`"
    )


class McpFeedbackSent(BaseModel):
    report_id: uuid.UUID = Field(description="Give it to the person if they ask")


class McpPerson(BaseModel):
    id: uuid.UUID = Field(description="Pass as `person_id` to change or remove them")
    name: str | None
    email: str
    role: AgencyRole
    all_workspaces: bool = Field(
        description="Reaches every workspace of the agency, including later ones"
    )
    workspace_ids: list[uuid.UUID] = Field(description="The workspaces they reach")
    can_approve: bool
    assistants: int = Field(description="How many assistants they have connected")
    is_you: bool = Field(description="The person you act for")


class McpInvite(BaseModel):
    id: uuid.UUID = Field(description="Pass as `person_id` to cancel the invite")
    email: str
    role: AgencyRole
    all_workspaces: bool
    workspace_ids: list[uuid.UUID]
    can_approve: bool
    expires_at: datetime
    invited_by: str | None


class McpPeople(BaseModel):
    agency: McpAgencyRef
    your_role: AgencyRole = Field(description="The role of the person you act for")
    workspaces: list[McpAgencyRef] = Field(
        description="The agency's workspaces, to read `workspace_ids` by name"
    )
    people: list[McpPerson]
    invites: list[McpInvite] = Field(
        description="Invites still waiting; empty unless your person is an admin"
    )


class McpInvited(BaseModel):
    sent: list[McpInvite]
    refused: list[dict[str, str]] = Field(
        description="Addresses that got no invite, each with `email`, `reason` "
        "(invalid, member or invited) and `message`"
    )


class McpRemoved(BaseModel):
    removed: Literal["person", "invite"]
    who: str
