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

from pydantic import BaseModel, Field, StringConstraints

from app.models.agent_list import AgentType
from app.models.call_list import CallListItemPublic, CallTilesPublic
from app.models.enums import (
    AssistantTaskState,
    FirstTurn,
    Platform,
    SpecRuleTouches,
    TaskKind,
)
from app.models.issue_list import IssueListItemPublic, IssueTilesPublic
from app.models.scenario import ScenarioPublic
from app.models.spec import SpecState
from app.models.test_run import (
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


class McpWorkspace(BaseModel):
    id: uuid.UUID
    name: str


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
    calls: int | None = Field(default=None, description="Calls in the period")
    latency_seconds: float | None = Field(
        default=None, description="Average of its calls' latencies in the period"
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


class McpStartedRun(BaseModel):
    run_id: uuid.UUID
    calls: int = Field(description="Simulated calls the run makes")


class McpTestRuns(BaseModel):
    """One run in detail when ``run_id`` was given; otherwise a tested version's
    results and the agent's runs."""

    run: TestRunDetailPublic | None = None
    results: VersionResultsPublic | None = Field(
        default=None,
        description="Without a run id: the tested version's results across its runs",
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


class McpAnswerClarifications(BaseModel):
    answers: list[McpClarificationDecision] = Field(max_length=50)


class McpArchiveIssue(BaseModel):
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ] = Field(description="Why, in the person's own words")
    duration: Literal["until_spike", "forever"] = "until_spike"


class McpUnarchiveIssue(BaseModel):
    reason: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=2000)
    ] = None


class McpIssues(BaseModel):
    tiles: IssueTilesPublic = Field(description="Counts for the agent and period")
    issues: list[IssueListItemPublic] = Field(description="Worst first")


class McpCalls(BaseModel):
    tiles: CallTilesPublic = Field(description="Counts for the filters and period")
    calls: list[CallListItemPublic]


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
