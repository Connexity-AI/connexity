"""Backend routes behind the MCP server's tools.

Every route answers in the standard shape (`McpAnswer`): the facts, the rules that
apply, numbered next steps and a guide. Every route except `/mcp/workspaces` is scoped
to a workspace in its path, resolved by `require_mcp_workspace`.
"""

import base64
import binascii
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import (
    McpAssistantName,
    McpCurrentUser,
    McpWorkspaceDep,
    SessionDep,
    require_mcp_user,
)
from app.core.config import settings
from app.core.encryption import decrypt
from app.crud import clarification as crud_clarification
from app.crud import scenario as crud_scenario
from app.crud import test_run as crud_test_run
from app.crud.call_list import CallFilters
from app.crud.issue_list import calls_by_agent, period_start
from app.crud.issue_page import (
    issue_calls_per_version,
    issue_findings_on_calls,
    latest_agent_version,
)
from app.crud.latency import agent_gap_percentiles
from app.models import (
    Agent,
    CallScreenPublic,
    CategoryPublic,
    IntegrationProvider,
    Platform,
    ReadinessPublic,
    ReadinessStepKey,
    ReadinessStepState,
    WorkspaceCreate,
)
from app.models.check import Issue
from app.models.clarification import (
    ClarificationListPublic,
    ClarificationPublic,
    ClarificationsAnsweredPublic,
)
from app.models.dashboard import DashboardPublic
from app.models.enums import (
    CallCheckStatus,
    ClarificationState,
    IssueState,
    RunStatus,
    TaskKind,
    VersionVerdict,
)
from app.models.issue_list import IssuePeriod, IssueStatusFilter
from app.models.mcp import (
    GUIDE_CALLS,
    GUIDE_CATEGORIES,
    GUIDE_CONNECT,
    GUIDE_FEEDBACK,
    GUIDE_GETTING_STARTED,
    GUIDE_ISSUES,
    GUIDE_READINESS,
    GUIDE_SCENARIOS,
    GUIDE_SPEC,
    GUIDE_WORKSPACES,
    McpAddAgents,
    McpAddedAgents,
    McpAgent,
    McpAgentPage,
    McpAnswer,
    McpAnswerClarifications,
    McpArchiveIssue,
    McpCallItem,
    McpCalls,
    McpConnection,
    McpConnectVoicePlatform,
    McpEndedTask,
    McpErrorDetail,
    McpFeedbackSent,
    McpHeldTask,
    McpIssue,
    McpIssueCheck,
    McpIssueFinding,
    McpIssues,
    McpIssueSetting,
    McpIssueVersion,
    McpMarkCritical,
    McpMarkFixed,
    McpNextTask,
    McpRaiseClarifications,
    McpRefusedAgent,
    McpRunScenarios,
    McpScanProgress,
    McpSendFeedback,
    McpStartedRun,
    McpTask,
    McpTaskCounts,
    McpTaskList,
    McpTaskRef,
    McpTestRuns,
    McpUnarchiveIssue,
    McpWorkspace,
    McpWriteScenarios,
    McpWriteScenarioSet,
    McpWriteSpec,
    McpWrittenScenarios,
)
from app.models.scenario import ScenarioListPublic, ScenarioSetPublic
from app.models.spec import SpecPublic, SpecWrittenPublic
from app.models.test_run import TestRunDetailPublic, VersionResultsPublic
from app.models.work import WorkMoveIn
from app.services.agent_list import agent_types, live_since
from app.services.agent_page import agent_page
from app.services.call_list import workspace_calls
from app.services.call_screen import call_screen
from app.services.checks.base import Check, ModelCheck
from app.services.checks.engine import current_mode
from app.services.checks.registry import get_check
from app.services.clarification import (
    AnswerDraft,
    ClarificationRefused,
    Decision,
    QuestionDraft,
    answer_clarifications,
    answered_public,
    clarifications_public,
    counts_public,
    raise_clarifications,
)
from app.services.connections import (
    KEY_LOCATION,
    VOICE_PLATFORMS,
    voice_platform_key_status,
    webhook_address,
)
from app.services.dashboard import dashboard
from app.services.feedback import DAILY_CAP as FEEDBACK_DAILY_CAP
from app.services.feedback import (
    FeedbackIn,
    FeedbackRefused,
    post_in_background,
    store_report,
)
from app.services.first_scan import SCAN_DAYS, scan_agents, scan_step
from app.services.issue_list import (
    IssueFilters,
    critical_issues_by_agent,
    workspace_issues,
)
from app.services.issue_page import issue_page
from app.services.onboarding import ANSWERS, SPECS, STEPS_BY_KEY, for_assistant
from app.services.onboarding_finish import finish_onboarding, onboarding_complete
from app.services.retell import (
    dedupe_retell_agents,
    list_retell_agents,
    retell_key_status,
)
from app.services.scenario import (
    FakeToolDraft,
    ScenarioDraft,
    ScenarioRefused,
    list_scenarios,
    scenario_public,
    write_scenario_set,
    write_scenarios,
)
from app.services.score import score, scores_by_agent
from app.services.spec import (
    RuleDraft,
    SpecRefused,
    agents_needing_specs,
    mark_critical_rules,
    spec_answer,
    spec_state,
    write_agent_spec,
)
from app.services.test_run import (
    CONVERSATION_CAP_MS,
    MAX_AGENT_REPLIES,
    RunRefused,
    RunRequest,
    launch,
    list_runs,
    run_detail,
    start_run,
    version_results,
    version_to_test,
)
from app.services.work import MoveRefused, Task, move_task, next_task, work_page

router = APIRouter(
    prefix="/mcp",
    tags=["mcp"],
    dependencies=[Depends(require_mcp_user)],
)

_CURSOR_PREFIX = "o:"
_CURSOR_MAX_OFFSET = 1_000_000_000
# The last next step of every tool that can finish a task.
NEXT_TASK = "When this task is done, call `get_next_task` for the next one."


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"{_CURSOR_PREFIX}{offset}".encode()).decode()


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        if not raw.startswith(_CURSOR_PREFIX):
            raise ValueError(raw)
        offset = int(raw.removeprefix(_CURSOR_PREFIX))
        if not 0 <= offset <= _CURSOR_MAX_OFFSET:
            raise ValueError(raw)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=McpErrorDetail(
                error="This cursor is not valid",
                next_steps=[
                    "Call the same tool without `cursor` to start from the first page, "
                    "then pass the `next_cursor` it returns."
                ],
            ).model_dump(),
        )
    return offset


def _mcp_agent(agent: Agent) -> McpAgent:
    return McpAgent(
        id=agent.id,
        name=agent.name,
        platform=agent.platform,
        platform_agent_id=agent.platform_agent_id,
        platform_agent_name=agent.platform_agent_name,
        created_at=agent.created_at,
    )


@router.get("/workspaces", response_model=McpAnswer[list[McpWorkspace]])
def list_workspaces(
    session: SessionDep, current_user: McpCurrentUser
) -> McpAnswer[list[McpWorkspace]]:
    workspaces = crud.list_accessible_workspaces(session=session, user=current_user)
    data = []
    for w in workspaces:
        found = score(session=session, company_id=w.id, with_moves=False)
        data.append(
            McpWorkspace(
                id=w.id, name=w.name, score=found.score, score_change=found.change
            )
        )
    return McpAnswer[list[McpWorkspace]](
        data=data,
        rules=[
            "score is the workspace's score over its checked calls in the last 30 "
            "days, with its change against the 30 days before; none before onboarding "
            "is complete or without a checked call. `get_agent` says what moves an "
            "agent's score.",
            "A workspace is one client's agents, calls and settings; nothing is "
            "shared between workspaces.",
            "You reach the workspaces the person who connected you can reach, and act "
            "on their behalf.",
        ],
        next_steps=[
            "Pass a workspace's `id` as `workspace_id` to every other Connexity tool.",
            "Call `list_agents` with that `workspace_id` to see its agents.",
        ],
        guide=GUIDE_WORKSPACES,
    )


@router.post("/workspaces", response_model=McpAnswer[McpWorkspace])
def create_workspace(
    session: SessionDep, current_user: McpCurrentUser, workspace_in: WorkspaceCreate
) -> McpAnswer[McpWorkspace]:
    name = workspace_in.name.strip()
    if not name:
        raise HTTPException(
            status_code=422,
            detail=McpErrorDetail(
                error="A workspace needs a name",
                next_steps=["Call `create_workspace` again with the client's name."],
                guide=GUIDE_WORKSPACES,
            ).model_dump(),
        )
    workspace = crud.create_workspace(session=session, user=current_user, name=name)
    return McpAnswer[McpWorkspace](
        data=McpWorkspace(id=workspace.id, name=workspace.name),
        rules=[
            "A workspace holds one client's agents, calls and settings; it starts empty.",
            "Only the person who created it is a member; there are no invitations yet.",
        ],
        next_steps=[
            "Pass this `id` as `workspace_id` to every tool that should act in it.",
            "Tell the person the workspace exists; they can open it from the profile "
            "menu in the web app.",
        ],
        guide=GUIDE_WORKSPACES,
    )


@router.get(
    "/workspaces/{workspace_id}/categories",
    response_model=McpAnswer[list[CategoryPublic]],
)
def list_categories(
    session: SessionDep, workspace: McpWorkspaceDep
) -> McpAnswer[list[CategoryPublic]]:
    # The same set for every workspace; the workspace keeps this route scoped like the
    # others, and leaves room for counts per category later.
    del workspace
    return McpAnswer[list[CategoryPublic]](
        data=[
            CategoryPublic(
                key=category.key,
                name=category.name,
                position=category.position,
                kind=category.kind,
            )
            for category in crud.list_categories(session=session)
        ],
        rules=[
            "One fixed set, the same for every workspace; only the Connexity team "
            "changes it.",
            "Group issues and spec rules under these categories, in this order, and "
            "use their names when you talk to the person.",
            "Behaviour categories describe what the agent does; technical ones are "
            "problems any agent can have, whatever its spec says.",
            "Every issue belongs to the category of the check that found it.",
        ],
        next_steps=[],
        guide=GUIDE_CATEGORIES,
    )


@router.get(
    "/workspaces/{workspace_id}/calls",
    response_model=McpAnswer[McpCalls],
)
def list_calls(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    query: str | None = Query(default=None, max_length=255),
    agent_id: uuid.UUID | None = Query(default=None),
    result: CallCheckStatus | None = Query(default=None),
    category: str | None = Query(default=None, max_length=64),
    period: Literal["7d", "30d", "90d"] = "30d",
    issue_id: uuid.UUID | None = Query(default=None),
    version: str | None = Query(default=None, max_length=64),
    cursor: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
) -> McpAnswer[McpCalls]:
    offset = _decode_cursor(cursor)
    page = workspace_calls(
        session=session,
        company_id=workspace.id,
        filters=CallFilters(
            period=period,
            agent_id=agent_id,
            result=result,
            category=category,
            query=query,
            issue_id=issue_id,
            version=version,
        ),
        offset=offset,
        limit=limit,
    )
    next_steps = []
    if page.has_more:
        next_steps.append(
            "Call `list_calls` again with `cursor` set to `next_cursor` for the next "
            "page."
        )
    if query and not page.data and offset == 0:
        next_steps.append(
            "No call matches. A number matches the end of the caller's number; "
            "anything else must be a whole call id (Connexity's or Retell's). Try a "
            "longer period."
        )
    if page.tiles.failed:
        next_steps.append(
            "Call `list_issues` to see what the failed calls have in common."
        )
    calls = [McpCallItem(**item.model_dump()) for item in page.data]
    if issue_id is not None:
        ids = [call.id for call in calls]
        found = issue_findings_on_calls(
            session=session, issue_id=issue_id, call_ids=ids
        )
        for call in calls:
            call.issue_findings = [
                McpIssueFinding(
                    event_ids=list(finding.event_keys),
                    detail=finding.detail,
                    effect=finding.effect,
                    check_version=finding.check_version,
                )
                for finding in found.get(call.id, [])
            ]
    return McpAnswer[McpCalls](
        data=McpCalls(tiles=page.tiles, calls=calls),
        rules=[
            "Calls come newest first; the tiles count every call matching the "
            "filters in the period, whatever the result filter.",
            "Callers are shown as their last four digits only; never ask Connexity or "
            "repeat a full number.",
            "A result is failed when a finding fails the call, degraded when one only "
            "flags it, clean when checks ran and found nothing, unchecked otherwise. "
            "Say whether the worst finding was found by code or a model (found_by).",
            "Findings of archived issues are left out of every call's result, worst "
            "finding and findings, until the issue is unarchived; with issue_id of an "
            "archived issue, its own findings are listed so its calls can be read.",
            "With issue_id, only the calls that issue was found on are listed, each with "
            "its moment (when it first happened in the call and how many times) and "
            "that issue's findings on it: the events each "
            "points at and its detail. `get_issue` says what each detail key means; "
            "`get_call` shows the events.",
            "Each call carries the agent version it ran on (agent_version); `version` "
            "keeps only that version's calls, so two versions compare by calling twice.",
        ],
        next_steps=next_steps,
        guide=GUIDE_CALLS,
        next_cursor=_encode_cursor(offset + limit) if page.has_more else None,
    )


@router.get(
    "/workspaces/{workspace_id}/calls/{call_id}",
    response_model=McpAnswer[CallScreenPublic],
)
def get_call(
    session: SessionDep, workspace: McpWorkspaceDep, call_id: uuid.UUID
) -> McpAnswer[CallScreenPublic]:
    call = crud.get_call(session=session, call_id=call_id, company_id=workspace.id)
    screen = call_screen(session=session, call=call) if call is not None else None
    if screen is None:
        raise HTTPException(
            status_code=404,
            detail=McpErrorDetail(
                error="Call not found in this workspace"
                if call is None
                else "This call has no transcript yet",
                next_steps=[
                    "Call `list_calls` to find the call; pass its `id`.",
                ],
                guide=GUIDE_CALLS,
            ).model_dump(),
        )
    next_steps = []
    if screen.findings:
        next_steps.append(
            "Call `list_issues` with this agent's id to see how often each finding "
            "happens across calls."
        )
    return McpAnswer[CallScreenPublic](
        data=screen,
        rules=[
            "The timeline is in order: turns (agent or caller) and tool calls with "
            "their arguments and result; secret-looking values are masked.",
            "Findings are worst first and point at the entry they sit on; say whether "
            "a rule or a model found each.",
            "Do not repeat a caller's name, address or other personal details back "
            "unless the person asks about this call.",
        ],
        next_steps=next_steps,
        guide=GUIDE_CALLS,
    )


@router.get(
    "/workspaces/{workspace_id}/issues",
    response_model=McpAnswer[McpIssues],
)
def list_issues(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    query: str | None = Query(default=None, max_length=255),
    agent_id: uuid.UUID | None = Query(default=None),
    category: str | None = Query(default=None, max_length=64),
    severity: Literal["critical", "warning"] | None = Query(default=None),
    status: IssueStatusFilter = "open",
    period: IssuePeriod = "30d",
    version: str | None = Query(default=None, max_length=64),
    cursor: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
) -> McpAnswer[McpIssues]:
    offset = _decode_cursor(cursor)
    if agent_id is not None and (
        crud.get_agent(session=session, agent_id=agent_id, company_id=workspace.id)
        is None
    ):
        raise HTTPException(
            status_code=404,
            detail=McpErrorDetail(
                error="Agent not found in this workspace",
                next_steps=["Call `list_agents` for this workspace's agent ids."],
                guide=GUIDE_ISSUES,
            ).model_dump(),
        )
    page, matching = workspace_issues(
        session=session,
        company_id=workspace.id,
        filters=IssueFilters(
            period=period,
            agent_id=agent_id,
            category=category,
            severity=severity,
            status=status,
            query=query,
            version=version,
        ),
    )
    issues = matching[offset : offset + limit]
    has_more = offset + limit < len(matching)
    next_steps = []
    if has_more:
        next_steps.append(
            "Call `list_issues` again with `cursor` set to `next_cursor` for the next "
            "page."
        )
    if issues:
        next_steps.append(
            "Call `get_issue` with an issue's id for its calls per day, the latest "
            "calls it hit and its history."
        )
    if not matching and offset == 0:
        if query or category or severity or status != "open":
            next_steps.append(
                "No issue matches. Clear the search or filters, or try a longer period "
                "or another status."
            )
        else:
            next_steps.append(
                "No open issues. Calls are checked within a minute of arriving; if the "
                "workspace has no calls, call `get_readiness`."
            )
    if category and category not in {c.value for c in page.categories}:
        next_steps.append("Call `list_categories` for the category keys.")
    return McpAnswer[McpIssues](
        data=McpIssues(tiles=page.tiles, issues=issues),
        rules=[
            "With `version`, only the issues found on that agent version's calls in the "
            "period are listed, each counting only those calls; the tiles too.",
            "Worst first: open or reopened Critical issues and reopened ones, then the "
            "other open ones, then by calls affected in the period.",
            "status defaults to open, which includes reopened. Open and reopened issues "
            "show whatever the period; a resolved one only if it was resolved in the "
            "period; archived ones always.",
            "The tiles follow agent_id and the period only, never the search or the "
            "other filters.",
            "Say how each issue was found: found_by code_based means deterministic "
            "code over the call; classifier or judge means a model.",
            "Give the size as 'in N of M calls' (calls_affected of calls_total, both in "
            "the period), and group by category when you list several.",
            "Never quote what a caller said or a tool's arguments back to the person "
            "unless they ask for one call.",
        ],
        next_steps=next_steps,
        guide=GUIDE_ISSUES,
        next_cursor=_encode_cursor(offset + limit) if has_more else None,
    )


def _mcp_issue(
    session: SessionDep, workspace: McpWorkspaceDep, issue_id: uuid.UUID
) -> Issue:
    issue = crud.get_issue(session=session, issue_id=issue_id, company_id=workspace.id)
    if issue is None:
        raise HTTPException(
            status_code=404,
            detail=McpErrorDetail(
                error="Issue not found in this workspace",
                next_steps=["Call `list_issues` for this workspace's issue ids."],
                guide=GUIDE_ISSUES,
            ).model_dump(),
        )
    return issue


_ISSUE_RULES = [
    "Give the size as 'in N of M calls' (tiles.calls_affected of tiles.calls_total, "
    "the last 30 days), and say how it was found: found_by code_based means "
    "deterministic code over the call; classifier or judge means a model.",
    "An affected call's moment is when the issue first happened in it, and how many "
    "times; open the call with `get_call` to see it.",
    "Archiving is the person's decision. Before `archive_issue` or `unarchive_issue`, "
    "say which issue, its size and the duration, and wait for the person's yes; put "
    "their words in the reason.",
    "While archived, the issue is hidden on every call, including earlier ones, and "
    "counts for nothing; until_spike brings it back as reopened when it starts "
    "happening twice as often.",
]


def _issue_check(check: Check) -> McpIssueCheck:
    model = check if isinstance(check, ModelCheck) else None
    return McpIssueCheck(
        type=check.type,
        title=check.title,
        description=check.description,
        kind=check.kind,
        version=check.version,
        provider=model.provider.value if model else None,
        model=model.model if model else None,
        needs=[need.value for need in check.needs],
        detail_fields=dict(check.detail_fields),
    )


def _issue_answer(
    session: SessionDep, issue: Issue, next_steps: list[str]
) -> McpAnswer[McpIssue]:
    summary = crud.summarise_issue(session=session, issue=issue)
    page = issue_page(session=session, issue=issue, summary=summary)
    check = get_check(issue.check_type)
    setting = None
    if check is not None:
        records = crud.check_setting_history(
            session=session, agent_id=issue.agent_id
        ).get(check.type, [])
        setting = McpIssueSetting(
            mode=current_mode(check, records),
            default=check.default_mode,
            since=records[-1].created_at if records else None,
        )
    detail = McpIssue(
        **page.model_dump(),
        check=_issue_check(check) if check else None,
        setting=setting,
        versions=[
            McpIssueVersion(version=version, calls=calls)
            for version, calls in issue_calls_per_version(
                session=session,
                issue_id=issue.id,
                since=datetime.now(UTC) - timedelta(days=30),
            )
        ],
        live_version=latest_agent_version(session=session, agent_id=issue.agent_id),
        findings_all_time=summary.finding_count,
        calls_all_time=summary.call_count,
    )
    if page.tiles.calls_affected:
        next_steps.append(
            f"Call `list_calls` with issue_id {issue.id} (and a `limit`) for the calls "
            "it was found on, with its findings in each."
        )
    return McpAnswer[McpIssue](
        data=detail, rules=_ISSUE_RULES, next_steps=next_steps, guide=GUIDE_ISSUES
    )


@router.get(
    "/workspaces/{workspace_id}/issues/{issue_id}",
    response_model=McpAnswer[McpIssue],
)
def get_issue(
    session: SessionDep, workspace: McpWorkspaceDep, issue_id: uuid.UUID
) -> McpAnswer[McpIssue]:
    issue = _mcp_issue(session, workspace, issue_id)
    next_steps = _fix_steps(issue)
    if issue.state is not IssueState.ARCHIVED:
        next_steps.append(
            "If the person decides nobody will fix it, ask them, then call "
            "`archive_issue` with their reason."
        )
    if crud.latest_spec(session=session, agent_id=issue.agent_id) is not None:
        next_steps.append(
            "If the agent's spec does not say whether this behaviour is allowed, raise "
            "a question with `raise_clarifications` and these calls as evidence."
        )
    return _issue_answer(session, issue, next_steps)


def _fix_steps(issue: Issue) -> list[str]:
    """Where the issue's fix stands."""
    version = issue.resolved_version
    if issue.state is IssueState.RESOLVED and version and issue.fix_live_at is None:
        return [
            f"Marked fixed in version {version}; waiting for version {version} to go "
            "live on real calls. Until then, nothing reopens it."
        ]
    if issue.state is IssueState.RESOLVED:
        return [
            f"Fixed{f' in version {version}' if version else ''} and live; it reopens "
            "if it happens again on a later call."
        ]
    if issue.state is IssueState.REOPENED and version:
        return [
            f"It came back after the fix in version {version} went live: read the new "
            "calls, fix it again, then call `mark_issue_fixed` with the new version."
        ]
    return []


@router.post(
    "/workspaces/{workspace_id}/issues/{issue_id}/fixed",
    response_model=McpAnswer[McpIssue],
)
def mark_issue_fixed(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    issue_id: uuid.UUID,
    body: McpMarkFixed,
) -> McpAnswer[McpIssue]:
    issue = _mcp_issue(session, workspace, issue_id)

    def refuse(error: str, step: str) -> HTTPException:
        return HTTPException(
            status_code=422,
            detail=McpErrorDetail(
                error=error, next_steps=[step, "Nothing changed."], guide=GUIDE_ISSUES
            ).model_dump(),
        )

    if issue.state is IssueState.ARCHIVED:
        raise refuse(
            "The issue is archived",
            "Ask the person to unarchive it (`unarchive_issue`) before marking it fixed.",
        )
    if issue.state is IssueState.RESOLVED and issue.resolved_version == body.version:
        raise refuse(
            f"The issue is already marked fixed in version {body.version}",
            "Call `get_issue` to see whether that version went live.",
        )
    found = crud.calls_found_on_version(
        session=session, issue=issue, fix_version=body.version
    )
    if found:
        raise refuse(
            f"This issue was found on {found} "
            f"{'call' if found == 1 else 'calls'} on version {body.version} or later; "
            "the fix is not in it",
            "Read those calls (`list_calls` with this issue_id), fix the agent, and "
            "mark it fixed in the version that carries the change.",
        )
    issue = crud.set_issue_state(
        session=session,
        issue_id=issue.id,
        state=IssueState.RESOLVED,
        version=body.version,
        reason=body.note or None,
        decided_by=current_user,
        assistant_name=assistant or "your assistant",
    )
    return _issue_answer(
        session,
        issue,
        [
            *_fix_steps(issue),
            "Tell the person it is marked fixed in version "
            f"{body.version}; it reopens by itself if it comes back.",
            NEXT_TASK,
        ],
    )


@router.post(
    "/workspaces/{workspace_id}/issues/{issue_id}/archive",
    response_model=McpAnswer[McpIssue],
)
def archive_issue(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    issue_id: uuid.UUID,
    body: McpArchiveIssue,
) -> McpAnswer[McpIssue]:
    issue = _mcp_issue(session, workspace, issue_id)
    if issue.state is IssueState.ARCHIVED:
        how = "until it spikes" if issue.archive_until_spike else "forever"
        return _issue_answer(
            session,
            issue,
            [
                f"It was already archived ({how}); nothing changed. To change how long, "
                "ask the person, call `unarchive_issue`, then `archive_issue` again."
            ],
        )
    issue = crud.set_issue_state(
        session=session,
        issue_id=issue.id,
        state=IssueState.ARCHIVED,
        version=None,
        reason=body.reason,
        decided_by=current_user,
        until_spike=body.duration == "until_spike",
        assistant_name=assistant or "your assistant",
    )
    return _issue_answer(
        session,
        issue,
        [
            "Tell the person it is archived and recorded as approved by them; "
            "`unarchive_issue` brings it back.",
            NEXT_TASK,
        ],
    )


@router.post(
    "/workspaces/{workspace_id}/issues/{issue_id}/unarchive",
    response_model=McpAnswer[McpIssue],
)
def unarchive_issue(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    issue_id: uuid.UUID,
    body: McpUnarchiveIssue,
) -> McpAnswer[McpIssue]:
    issue = _mcp_issue(session, workspace, issue_id)
    if issue.state is IssueState.ARCHIVED:
        issue = crud.set_issue_state(
            session=session,
            issue_id=issue.id,
            state=IssueState.OPEN,
            version=None,
            reason=body.reason or None,
            decided_by=current_user,
            assistant_name=assistant or "your assistant",
        )
        steps = ["Its calls count again, including those from while it was archived."]
    else:
        steps = ["It was not archived; nothing changed."]
    return _issue_answer(session, issue, steps)


@router.get(
    "/workspaces/{workspace_id}/agents",
    response_model=McpAnswer[list[McpAgent]],
)
def list_agents(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    query: str | None = Query(default=None, max_length=255),
    period: Literal["7d", "30d", "90d"] = "30d",
    cursor: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
) -> McpAnswer[list[McpAgent]]:
    offset = _decode_cursor(cursor)
    search = query.strip() if query else None
    agents, has_more = crud.search_agents(
        session=session,
        company_id=workspace.id,
        query=search or None,
        offset=offset,
        limit=limit,
    )
    next_steps = []
    if has_more:
        next_steps.append(
            "Call `list_agents` again with `cursor` set to `next_cursor` for the next "
            "page."
        )
    if search and not agents and offset == 0:
        next_steps.append(
            "No agent's name matches. Call `list_agents` without `query` to see them all."
        )
    ids = [agent.id for agent in agents]
    specs = crud.latest_specs(session=session, agent_ids=ids)
    currents = crud.current_agent_versions(session=session, agent_ids=ids)
    types = agent_types(session=session, agents=list(agents), currents=currents)
    latency = agent_gap_percentiles(
        session=session, agent_ids=ids, since=period_start(period)
    )
    calls = calls_by_agent(
        session=session, company_id=workspace.id, since=period_start(period)
    )
    critical = critical_issues_by_agent(
        session=session, company_id=workspace.id, period=period
    )
    onboarded = onboarding_complete(session=session, company_id=workspace.id)
    scores = scores_by_agent(
        session=session, company_id=workspace.id, period=period, onboarded=onboarded
    )
    data = []
    for agent in agents:
        row = _mcp_agent(agent)
        row.score, row.score_change = scores.get(agent.id, (None, None))
        row.type = types.get(agent.id)
        row.calls = calls.get(agent.id, 0)
        row.critical_issues = critical.get(agent.id, 0)
        if agent.id in latency:
            row.latency_p50 = latency[agent.id].p50
            row.latency_p95 = latency[agent.id].p95
        row.live_version = currents.get(agent.id)
        row.live_since = live_since(
            session=session, agent=agent, version=row.live_version
        )
        spec = specs.get(agent.id)
        row.spec = spec_state(spec, currents.get(agent.id))
        row.spec_version = spec.version if spec else None
        data.append(row)
    waiting = [
        row.name for row in data if row.spec != "current" and currents.get(row.id)
    ]
    if waiting:
        next_steps.append(
            f"{len(waiting)} {'agent has' if len(waiting) == 1 else 'agents have'} no "
            "spec, or one to review: call `get_spec` and then `write_spec` for each, "
            "following connexity://guides/spec."
        )
    return McpAnswer[list[McpAgent]](
        data=data,
        rules=[
            _SCORE_RULE,
            "Connexity never edits, deploys or calls an agent; it records and checks "
            "what the agent does.",
            "Agents are listed newest first; `query` matches part of the name, "
            "ignoring case.",
            "calls counts the agent's calls in the period (30d by default); type is "
            "read from its current version, and is empty until Connexity has read it.",
            _LATENCY_RULE,
        ],
        next_steps=next_steps,
        guide=GUIDE_GETTING_STARTED,
        next_cursor=_encode_cursor(offset + limit) if has_more else None,
    )


def _mcp_agent_in(
    session: SessionDep, workspace: McpWorkspaceDep, agent_id: uuid.UUID
) -> Agent:
    agent = crud.get_agent(session=session, agent_id=agent_id, company_id=workspace.id)
    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=McpErrorDetail(
                error="Agent not found in this workspace",
                next_steps=["Call `list_agents` for this workspace's agent ids."],
                guide=GUIDE_SPEC,
            ).model_dump(),
        )
    return agent


_SPEC_RULES = [
    "Write rules only for what the prompt settles, each with the prompt's words it rests "
    "on; behaviour the prompt does not settle is a question for the person, never a "
    "rule.",
    "Read the prompt from the voice platform, never from Connexity, for the version the "
    "agent's calls run on (current_agent_version), not a draft: Connexity checks every "
    "quote against the prompt it recorded for that version.",
    "Keep a rule across versions by passing its key; a kept rule without its key reads "
    "as dropped and added again.",
    "Rules are never edited: every `write_spec` is a new version, and earlier versions "
    "stay as they were.",
    "in_conflict means an open question replaces the rule; answering it changes the "
    "rule. With compare, each rule is kept, added or dropped against that version; a "
    "rule whose text changed reads as dropped and added.",
    "Rules with source clarification are the person's answers: Connexity carries them "
    "into every version; never pass them to `write_spec`. To change one, raise a "
    "clarification that replaces it.",
    "A critical rule is one whose failure must stop a release; a failure of any other "
    "rule is a Warning. Marking is yours to decide, without asking the person: mark "
    "with `critical` in `write_spec` or with `mark_critical_rules`. Marks carry into "
    "every later version by key. When unsure, not critical.",
]


def _spec_refused(refused: SpecRefused, retry: str) -> HTTPException:
    """Every problem, at most 20 listed, then how to try again."""
    more = len(refused.problems) - 20
    return HTTPException(
        status_code=422,
        detail=McpErrorDetail(
            error=refused.error,
            next_steps=[
                *refused.problems[:20],
                *([f"… and {more} more problems like these."] if more > 0 else []),
                retry,
            ],
            guide=GUIDE_SPEC,
        ).model_dump(),
    )


def _scenario_step(answer: SpecPublic, agent_id: uuid.UUID) -> str | None:
    """Names the rules no scenario lists, critical first; None when there are none."""
    rules = [r for g in answer.groups for r in g.rules if r.change != "dropped"]
    unlisted = sorted(
        (r for r in rules if r.scenarios == 0), key=lambda r: not r.critical
    )
    if not unlisted:
        return None
    critical = sum(1 for r in unlisted if r.critical)
    first = ", ".join(f"'{r.key}'" for r in unlisted[:5])
    which = f", {critical} of them critical" if critical else ""
    return (
        f"Write scenarios for the {len(unlisted)} "
        f"{'rule' if len(unlisted) == 1 else 'rules'} no scenario lists{which} "
        f"(`write_scenarios` with agent_id {agent_id}), starting with {first}; follow "
        f"{GUIDE_SCENARIOS}."
    )


def _critical_step(answer: SpecPublic, agent_id: uuid.UUID) -> str:
    counts = answer.counts
    critical = counts.critical if counts else 0
    total = counts.from_prompt + counts.from_clarifications if counts else 0
    if critical == 0:
        return (
            "No rule is marked critical. Mark the rules whose failure must stop a "
            f"release with `mark_critical_rules` (agent_id {agent_id}), following "
            'connexity://guides/spec, "Critical rules".'
        )
    return (
        f"{critical} of the spec's {total} rules "
        f"{'is' if critical == 1 else 'are'} critical; change marks with "
        "`mark_critical_rules` if the spec changed what matters."
    )


def _waiting_step(
    session: SessionDep, company_id: uuid.UUID, agent_id: uuid.UUID | None = None
) -> str | None:
    """How many questions wait for the person, as a next step; None when none do."""
    if agent_id is not None:
        count = crud_clarification.state_counts(
            session=session, company_id=company_id, agent_id=agent_id
        )[ClarificationState.OPEN]
        where = "on this agent"
    else:
        per_agent = crud_clarification.open_counts(
            session=session, company_id=company_id
        )
        count = sum(per_agent.values())
        agents = len(per_agent)
        where = f"on {agents} {'agent' if agents == 1 else 'agents'}"
    if not count:
        return None
    return _waiting_text(count, agent_id, where)


def _waiting_text(
    count: int, agent_id: uuid.UUID | None, where: str = "on this agent"
) -> str:
    agent_arg = f" with agent_id {agent_id}" if agent_id is not None else ""
    return (
        f"{count} {'question waits' if count == 1 else 'questions wait'} for the person "
        f"{where}: call `list_clarifications`{agent_arg}, then confirm the answers with "
        "them and call `answer_clarifications`."
    )


def _spec_steps(answer: SpecPublic) -> list[str]:
    steps = []
    if answer.current_agent_version is None:
        steps.append(
            "The agent has no calls yet, so its version is not known; write its spec "
            "after its first call."
        )
    elif answer.state == "none":
        steps.append(
            "Write the spec: read the agent's prompt and config from the voice "
            "platform with your own access, for the version its calls run on (the "
            "published one, not a draft), then `write_spec`."
        )
    elif answer.state == "needs_review":
        steps.append(
            f"The agent moved to version {answer.current_agent_version}; Connexity "
            "copied the previous spec to it. Compare the prompts, keep what holds (with "
            "keys), and write what changed with `write_spec`. Raise what the change "
            "leaves unsettled with `raise_clarifications`, and replace (`replaces_key`) "
            "any answered rule it contradicts."
        )
    return steps


@router.get(
    "/workspaces/{workspace_id}/agents/{agent_id}/spec",
    response_model=McpAnswer[SpecPublic],
)
def get_spec(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    agent_id: uuid.UUID,
    version: int | None = Query(default=None, ge=1),
    compare: int | None = Query(default=None, ge=1),
) -> McpAnswer[SpecPublic]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    answer = spec_answer(
        session=session,
        agent=agent,
        version=version,
        compare=compare,
    )
    if answer is None:
        asked = ", ".join(str(v) for v in (version, compare) if v is not None)
        raise HTTPException(
            status_code=404,
            detail=McpErrorDetail(
                error=f"The agent has no spec version {asked}",
                next_steps=[
                    "Call `get_spec` without a version for the latest; its `versions` "
                    "lists every version."
                ],
                guide=GUIDE_SPEC,
            ).model_dump(),
        )
    steps = _spec_steps(answer)
    if answer.open_clarifications:
        steps.append(_waiting_text(answer.open_clarifications, agent.id))
    return McpAnswer[SpecPublic](
        data=answer, rules=_SPEC_RULES, next_steps=steps, guide=GUIDE_SPEC
    )


@router.post(
    "/workspaces/{workspace_id}/agents/{agent_id}/spec",
    response_model=McpAnswer[SpecWrittenPublic],
)
def write_spec(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    agent_id: uuid.UUID,
    body: McpWriteSpec,
) -> McpAnswer[SpecWrittenPublic]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    try:
        written = write_agent_spec(
            session=session,
            agent=agent,
            drafts=[
                RuleDraft(
                    text=r.text,
                    category=r.category,
                    quote=r.quote,
                    touches=r.touches,
                    key=r.key or None,
                    critical=r.critical,
                )
                for r in body.rules
            ],
            author=current_user,
            assistant_name=assistant or "your assistant",
        )
    except SpecRefused as refused:
        raise _spec_refused(
            refused,
            "Fix these and call `write_spec` again with every rule; nothing was stored.",
        ) from None
    steps = []
    changes = written.changes
    if changes.kept == 0 and written.spec and written.spec.version > 1:
        steps.append(
            "No rule kept its key from the previous version. If you meant to keep rules, "
            "write the spec again passing their keys."
        )
    if not changes.quotes_checked:
        steps.append(
            "Connexity has no recorded prompt for this version, so quotes were not "
            "checked."
        )
    if changes.carried:
        steps.append(
            f"{changes.carried} rules from the person's answers were carried over "
            "unchanged."
        )
    steps.append(
        f"Look at the agent's recent calls (`list_calls` with agent_id {agent.id}) for "
        "behaviour these rules do not settle, and raise each as a question with "
        "`raise_clarifications`, following connexity://guides/spec."
    )
    steps.append(_critical_step(written, agent.id))
    if (scenarios := _scenario_step(written, agent.id)) is not None:
        steps.append(scenarios)
    steps.append("Tell the person the spec is written, and what you raised.")
    steps.append(NEXT_TASK)
    return McpAnswer[SpecWrittenPublic](
        data=written, rules=_SPEC_RULES, next_steps=steps, guide=GUIDE_SPEC
    )


@router.post(
    "/workspaces/{workspace_id}/agents/{agent_id}/spec/critical",
    response_model=McpAnswer[SpecPublic],
)
def mark_critical(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    agent_id: uuid.UUID,
    body: McpMarkCritical,
) -> McpAnswer[SpecPublic]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    try:
        answer, changed = mark_critical_rules(
            session=session,
            agent=agent,
            critical=body.critical,
            not_critical=body.not_critical,
            author=current_user,
            assistant_name=assistant or "your assistant",
        )
    except SpecRefused as refused:
        raise _spec_refused(
            refused,
            "Fix these and call `mark_critical_rules` again; no rule was marked.",
        ) from None
    version = answer.spec.version if answer.spec else None
    steps = [
        (
            f"{changed} {'rule' if changed == 1 else 'rules'} changed; spec version "
            f"{version} has them."
            if changed
            else "Every rule already had that mark; no version was made."
        ),
        _critical_step(answer, agent.id),
        *([step] if (step := _scenario_step(answer, agent.id)) else []),
        "Tell the person which rules are critical, in a line: they can ask you to "
        "change it.",
        NEXT_TASK,
    ]
    return McpAnswer[SpecPublic](
        data=answer, rules=_SPEC_RULES, next_steps=steps, guide=GUIDE_SPEC
    )


_CLARIFICATION_RULES = [
    "A clarification is a question about behaviour the agent's spec does not settle. "
    "Each answer carries the rule it becomes; the chosen answer's rule is added to the "
    "spec in a new version.",
    "The person answers. Ask them in your chat and confirm every answer with them before "
    "`answer_clarifications`; you may tell them what you would pick and why. Connexity "
    "records only the answer. When they leave a decision to you, it is still recorded "
    "as theirs, with you as the assistant that acted; tell them so.",
    "When the person's answer is none of the choices, answer `other` with their words as "
    "`text`: it becomes the rule as written.",
    "An answer is final. To change one, raise a clarification that replaces its rule "
    "(`replaces_key`), quoting the earlier answer.",
    "You may propose answers where the spec, the prompt or the calls support them, "
    "saying why; the person confirms them, as a batch if they like. Mark an answer "
    "they confirmed from your proposal `proposed`; never send one they have not seen.",
    "calls_seen counts the calls given as evidence; a question raised from a prompt "
    "change may have none.",
    "Open questions are listed most important first: seen on more calls, then touching "
    "money, safety or compliance, then the newest. Answered and parked ones newest "
    "first. A parked question can be answered, or reopened with `reopen`.",
]


def _refused(refused: ClarificationRefused, retry: str) -> HTTPException:
    problems = refused.problems
    return HTTPException(
        status_code=422,
        detail=McpErrorDetail(
            error=refused.error,
            next_steps=[
                *problems[:20],
                *(
                    [f"… and {len(problems) - 20} more problems like these."]
                    if len(problems) > 20
                    else []
                ),
                retry,
            ],
            guide=GUIDE_SPEC,
        ).model_dump(),
    )


@router.post(
    "/workspaces/{workspace_id}/agents/{agent_id}/clarifications",
    response_model=McpAnswer[list[ClarificationPublic]],
)
def raise_agent_clarifications(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    agent_id: uuid.UUID,
    body: McpRaiseClarifications,
) -> McpAnswer[list[ClarificationPublic]]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    try:
        stored = raise_clarifications(
            session=session,
            agent=agent,
            drafts=[
                QuestionDraft(
                    question=q.question,
                    answers=[AnswerDraft(a.label, a.rule) for a in q.answers],
                    category=q.category,
                    touches=q.touches,
                    call_ids=q.call_ids,
                    replaces_key=q.replaces_key or None,
                )
                for q in body.questions
            ],
            raised_by=current_user,
            assistant_name=assistant or "your assistant",
        )
    except ClarificationRefused as refused:
        raise _refused(
            refused,
            "Fix these and call `raise_clarifications` again with every question; "
            "nothing was stored.",
        ) from None
    return McpAnswer[list[ClarificationPublic]](
        data=clarifications_public(session=session, rows=stored),
        rules=_CLARIFICATION_RULES,
        next_steps=[
            "Ask the person in your chat, one question at a time or in one batch, then "
            "call `answer_clarifications` with what they pick. Never answer without "
            "them. They can also answer in Connexity.",
            NEXT_TASK,
        ],
        guide=GUIDE_SPEC,
    )


@router.get(
    "/workspaces/{workspace_id}/clarifications",
    response_model=McpAnswer[ClarificationListPublic],
)
def list_clarifications(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    agent_id: uuid.UUID | None = None,
    state: ClarificationState = ClarificationState.OPEN,
    cursor: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=20, ge=1, le=50),
) -> McpAnswer[ClarificationListPublic]:
    if agent_id is not None:
        _mcp_agent_in(session, workspace, agent_id)
    offset = _decode_cursor(cursor)
    rows, has_more = crud_clarification.list_page(
        session=session,
        company_id=workspace.id,
        state=state,
        agent_id=agent_id,
        offset=offset,
        limit=limit,
    )
    counts = counts_public(session=session, company_id=workspace.id, agent_id=agent_id)
    steps = []
    if has_more:
        steps.append(
            "Call `list_clarifications` again with `cursor` set to `next_cursor` for "
            "the next page."
        )
    if state is ClarificationState.OPEN and rows:
        steps.append(
            "Ask the person in your chat, then call `answer_clarifications` with what "
            "they pick; park what is not important now."
        )
    if not rows and state is ClarificationState.OPEN:
        steps.append("No questions wait for the person.")
    return McpAnswer[ClarificationListPublic](
        data=ClarificationListPublic(
            counts=counts, data=clarifications_public(session=session, rows=rows)
        ),
        rules=_CLARIFICATION_RULES,
        next_steps=steps,
        guide=GUIDE_SPEC,
        next_cursor=_encode_cursor(offset + limit) if has_more else None,
    )


@router.post(
    "/workspaces/{workspace_id}/clarifications/answers",
    response_model=McpAnswer[ClarificationsAnsweredPublic],
)
def answer_workspace_clarifications(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    body: McpAnswerClarifications,
) -> McpAnswer[ClarificationsAnsweredPublic]:
    try:
        result = answer_clarifications(
            session=session,
            company_id=workspace.id,
            decisions=[
                Decision(a.clarification_id, a.answer, a.text, a.proposed)
                for a in body.answers
            ],
            decided_by=current_user,
            assistant_name=assistant or "your assistant",
        )
    except ClarificationRefused as refused:
        raise _refused(
            refused,
            "Fix these and call `answer_clarifications` again with every answer; "
            "nothing was recorded.",
        ) from None
    finished = finish_onboarding(session=session, company_id=workspace.id)
    data = answered_public(session=session, company_id=workspace.id, result=result)
    steps = [
        *([_dashboard_ready(session, workspace.id)] if finished else []),
        "Tell the person what was recorded: their answers are now spec rules, carried "
        "into every later version, and recorded as theirs.",
    ]
    if data.open:
        steps.append(
            f"{data.open} {'question is' if data.open == 1 else 'questions are'} still "
            "open: call `list_clarifications`."
        )
    steps.append(NEXT_TASK)
    return McpAnswer[ClarificationsAnsweredPublic](
        data=data, rules=_CLARIFICATION_RULES, next_steps=steps, guide=GUIDE_SPEC
    )


_LATENCY_RULE = (
    "Latency is p50 and p95 over every reply in the period: the time from the caller "
    "finishing to the agent starting to answer, as the Dashboard measures it. Turns "
    "where the agent starts before the caller finishes are not counted. Give it as "
    '"1.6s/3.1s (p50/p95) over 840 replies"; latency_days gives each day\'s p50.'
)


@router.get(
    "/workspaces/{workspace_id}/agents/{agent_id}",
    response_model=McpAnswer[McpAgentPage],
)
def get_agent(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    agent_id: uuid.UUID,
    period: Literal["7d", "30d", "90d"] = "30d",
    version: str | None = Query(default=None, max_length=64),
) -> McpAnswer[McpAgentPage]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    page = McpAgentPage(
        **{
            **agent_page(
                session=session, agent=agent, period=period, version=version
            ).model_dump(),
            # The assistant also gets what moves the score.
            "score": score(
                session=session,
                company_id=workspace.id,
                period=period,
                agent_id=agent.id,
                version=version,
            ),
        }
    )
    scope = f" and version {version}" if version else ""
    next_steps = [
        f"Call `list_calls` with agent_id {agent.id}{scope} for its calls, and "
        "`list_issues` with the same for what was found on them."
    ]
    if version is None and len(page.versions) > 1:
        newest, before = page.versions[0].version, page.versions[1].version
        next_steps.append(
            f"To compare versions, call `get_agent` with version {newest} and again "
            f"with version {before}."
        )
    if page.spec != "current" and page.live_version:
        next_steps.append(
            "The agent's spec is missing or needs review: call `get_spec` and "
            "`write_spec`, following connexity://guides/spec. When it needs review, raise "
            "what the new version leaves unsettled with `raise_clarifications`."
        )
    waiting = _waiting_step(session, workspace.id, agent.id)
    if waiting:
        next_steps.append(waiting)
    if page.score and page.score.moves:
        worst = page.score.moves[0]
        next_steps.append(
            f"What costs the score most: {worst.title} ({worst.points} points over "
            f"{worst.calls} calls); call `get_issue` with issue_id {worst.issue_id}."
        )
    return McpAnswer[McpAgentPage](
        data=page,
        rules=[
            _SCORE_RULE,
            _LATENCY_RULE,
            "live_version is the agent version of its most recent call, and live_since "
            "when the first call on it started.",
            "systems are the n8n workflows its tool calls ran in the period.",
            "critical_issues counts its open or reopened critical issues that showed in "
            "the period, as the Issues page's Critical tile does; `list_issues` with "
            "agent_id and severity critical lists them.",
            "versions lists every agent version that has a call, the latest call's "
            "first; with `version`, calls, latency, systems and the score count only "
            "that version's calls in the period.",
        ],
        next_steps=next_steps,
        guide=GUIDE_GETTING_STARTED,
    )


_SCORE_RULE = (
    "The score is 100 x (1 - (failed + 0.5 x degraded) / checked calls) in the period, "
    'a basic formula that will be replaced. Give it with its base ("78 over 412 '
    'checked calls in 30 days") and its change against the previous period. Only '
    "fixes and improvements should raise it; there is none before onboarding is "
    "complete or without a checked call (why_none says which). moves lists the issues "
    "that cost the most points."
)


_TASK_RULES = [
    "Connexity sorts the workspace's tasks; take them in its order and do not pick "
    "your own. The order: incidents, then Critical tasks, then setup (onboarding steps, "
    "then specs, then the open questions while onboarding runs), then everything else, "
    "most calls first. A task that blocks a higher one sits above it.",
    "Asking for your next task ends this one: done when its work is gone; otherwise it "
    "goes back to its place in the list. A review of calls is done once handed out. An "
    "issue fix stays with your session until the issue is resolved or archived; put it "
    "back with `move_task` if you stop working on it.",
    "Only questions wait for the person. A task your session has not touched for 30 "
    "minutes shows as quiet on Work; ask for your next task to show you are working.",
    "Tasks are held per session: the person, the assistant and the session's name. "
    "Another session's task in progress is never handed to you. Tasks come from this "
    "workspace only.",
    "Name your session in a few words for the work it is on, such as `Onboarding`, and "
    "pass the same `session` on every `get_next_task` in it.",
    "Tasks waiting for the person are theirs: ask them in your chat, and never decide "
    "for them.",
    "A blocked task is never handed out: it waits for the tasks under Blocked by. A "
    "task that blocks others sits above them. Connexity works this out itself.",
]


def _named(keys: list[str], titles: dict[str, str]) -> str:
    first = titles.get(keys[0], keys[0])
    return f"{first} + {len(keys) - 1} more" if len(keys) > 1 else first


def _task_public(
    task: Task, titles: dict[str, str], position: int | None = None
) -> McpTask:
    facts = list(task.facts)
    if task.blocks:
        facts.append(f"Blocks: {_named(task.blocks, titles)}")
    if task.blocked_by:
        facts.append(f"Blocked by: {_named(task.blocked_by, titles)}")
    return McpTask(
        key=task.key,
        kind=task.kind,
        title=task.title,
        position=position,
        agent_id=task.agent_id,
        agent_name=task.agent_name,
        facts=facts,
        waiting_for_person=task.for_person,
        blocks=[McpTaskRef(key=k, title=titles.get(k, k)) for k in task.blocks[:5]],
        blocks_count=len(task.blocks),
        blocked_by=[
            McpTaskRef(key=k, title=titles.get(k, k)) for k in task.blocked_by[:5]
        ],
        blocked_by_count=len(task.blocked_by),
    )


def _task_steps(task: Task) -> list[str]:
    agent = f"`{task.agent_id}`"
    if task.kind is TaskKind.ONBOARDING:
        step = STEPS_BY_KEY.get(task.key.removeprefix("onboarding:"))
        own = [for_assistant(item.text) for item in step.instructions] if step else []
        if step is not None and step.key == ANSWERS:
            return own
        return [
            *own,
            "Call `get_readiness` to see where setup stands and do its next step with "
            "the person; follow connexity://guides/readiness.",
        ]
    if task.kind is TaskKind.SPEC:
        return [
            f"Read connexity://guides/spec and call `get_spec` for agent {agent}. Read "
            "its prompt and config from the voice platform with your own access, for "
            "the version its calls run on (the published one, not a draft).",
            "Write the rules the prompt settles with `write_spec`.",
            "Raise what the prompt does not settle with `raise_clarifications`; the "
            "person answers it.",
        ]
    if task.kind is TaskKind.TESTS:
        return [
            f"Read {GUIDE_SCENARIOS}, then call `list_scenarios` for agent {agent}: "
            "`unlisted_rules` names the rules without a scenario, critical first.",
            "Write scenarios for them with `write_scenarios`, using the rule keys from "
            "`get_spec`.",
            'Put a few that cover the critical rules in a "smoke" set with '
            "`write_scenario_set`.",
        ]
    if task.kind is TaskKind.CALLS_TO_REVIEW:
        return [
            f"Call `list_calls` with agent_id {agent}, result `unchecked` and period "
            "`7d`, and open a few with `get_call`.",
            "Tell the person why they could not be checked (for example no tool calls, "
            "or no recording), and what that hides.",
            "Raise behaviour the spec does not settle with `raise_clarifications`.",
        ]
    if task.kind is TaskKind.ISSUE_FIX:
        return [
            f"Call `get_issue` with issue_id `{task.ref}` for everything about it: the "
            "check behind it, what its findings record, its setting and the versions "
            "it was found on.",
            f"Call `list_calls` with issue_id `{task.ref}` (and a `limit`) for the "
            "calls it was found on with its findings in each; open any call in full "
            "with `get_call`. Find the cause.",
            "Propose the fix to the person. A change to the agent is made with their "
            "approval, outside Connexity; Connexity never changes an agent.",
            "Once the version with the fix is live, call `mark_issue_fixed` with that "
            "version. If the person decides not to fix it, `archive_issue` with their "
            "reason.",
        ]
    return []


def _waiting_steps(waiting: list[Task]) -> list[str]:
    steps = []
    # Only questions wait for the person (Dmytro, 2026-11-18).
    questions = [t for t in waiting if t.kind is TaskKind.CLARIFICATIONS]
    if questions:
        names = ", ".join(t.agent_name or "" for t in questions[:3])
        steps.append(
            f"Questions wait for the person on {names}: ask them in your chat "
            "(`list_clarifications` with the agent_id), then `answer_clarifications` "
            "with what they pick. If they want to leave them, move on: they can answer "
            "in Connexity."
        )
    return steps


def _dashboard_ready(session: SessionDep, company_id: uuid.UUID) -> str:
    """The step for the moment onboarding completes: the dashboard is ready."""
    page = dashboard(session=session, company_id=company_id)
    link = f"{settings.public_site_url or ''}/dashboard"
    base = f"{page.calls} {'call' if page.calls == 1 else 'calls'} in the last 30 days"
    found = (
        f"score {page.score.score}, {page.failed} failed calls"
        if page.score.score is not None
        else f"{page.failed} failed calls"
    )
    return (
        f'Onboarding is complete. Tell the person "Your dashboard is ready": {link}, '
        f"with what it shows first ({found}, over {base}), then what comes next."
    )


@router.get(
    "/workspaces/{workspace_id}/next-task",
    response_model=McpAnswer[McpNextTask],
)
def get_next_task(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    session_name: str | None = Query(
        default=None,
        alias="session",
        max_length=40,
        description="This session's name, the same on every call in it",
    ),
) -> McpAnswer[McpNextTask]:
    finished = finish_onboarding(session=session, company_id=workspace.id)
    result = next_task(
        session=session,
        company_id=workspace.id,
        person=current_user,
        assistant_name=assistant,
        session_name=session_name,
    )
    steps: list[str] = [_dashboard_ready(session, workspace.id)] if finished else []
    steps.extend(_waiting_steps(result.waiting))
    readiness_percent = None
    if result.task is not None:
        steps.extend(_task_steps(result.task))
        steps.append(NEXT_TASK)
    else:
        readiness_percent = crud.get_readiness(
            session=session, company_id=workspace.id, mcp_url=None
        ).percent
        if result.blocked:
            steps.append(
                f"Nothing you can take now: {result.blocked} "
                f"{'task is' if result.blocked == 1 else 'tasks are'} blocked by tasks "
                "that wait for the person or for another session. Help the person with "
                "the waiting ones above, then call `get_next_task` again."
            )
        else:
            steps.append(
                "Nothing else waits for you in this workspace. Call `get_next_task` "
                "again later, or after the person acts."
            )
    return McpAnswer[McpNextTask](
        data=McpNextTask(
            task=_task_public(result.task, result.titles, result.position)
            if result.task
            else None,
            previous=McpEndedTask(title=result.ended.title, state=result.ended.state)
            if result.ended
            else None,
            waiting_for_person=[
                _task_public(t, result.titles) for t in result.waiting[:10]
            ],
            in_progress=[
                McpHeldTask(
                    task=_task_public(h.task, result.titles, h.position),
                    person=h.person,
                    assistant=h.assistant,
                    session=h.session,
                )
                for h in result.held[:10]
            ],
            counts=McpTaskCounts(
                to_do=result.to_do,
                waiting_for_person=len(result.waiting),
                in_progress_elsewhere=result.in_progress_elsewhere,
                blocked=result.blocked,
            ),
            readiness_percent=readiness_percent,
        ),
        rules=_TASK_RULES,
        next_steps=steps,
        guide=GUIDE_GETTING_STARTED,
    )


@router.get(
    "/workspaces/{workspace_id}/tasks",
    response_model=McpAnswer[McpTaskList],
)
def list_tasks(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    cursor: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
) -> McpAnswer[McpTaskList]:
    offset = _decode_cursor(cursor)
    page = work_page(session=session, company_id=workspace.id)
    tasks = sorted(page.in_progress + page.to_do, key=lambda t: t.position)
    shown = tasks[offset : offset + limit]
    more = offset + limit < len(tasks)
    steps = []
    if more:
        steps.append(
            "Call `list_tasks` again with `cursor` set to `next_cursor` for the next "
            "page."
        )
    steps.append(
        "This only reads the list. To take your next task, call `get_next_task`."
    )
    return McpAnswer[McpTaskList](
        data=McpTaskList(
            tasks=shown,
            done=page.done[:20],
            sessions=page.sessions,
            waiting=page.waiting,
            total=len(tasks),
        ),
        rules=[
            "The list is the Work page's, in Connexity's order: the order "
            "`get_next_task` hands tasks out in.",
            "in_progress is held by a session; waiting is the person's to move on; to_do "
            "is free unless Blocked by lists a task.",
            "Done covers the last 7 days.",
        ],
        next_steps=steps,
        guide=GUIDE_GETTING_STARTED,
        next_cursor=_encode_cursor(offset + limit) if more else None,
    )


@router.post(
    "/workspaces/{workspace_id}/tasks/move",
    response_model=McpAnswer[McpTaskList],
)
def move_workspace_task(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    body: WorkMoveIn,
) -> McpAnswer[McpTaskList]:
    try:
        move_task(
            session=session,
            company_id=workspace.id,
            key=body.key,
            before=body.before,
            person=current_user,
            assistant_name=assistant or "your assistant",
        )
    except MoveRefused as refused:
        raise HTTPException(
            status_code=422,
            detail=McpErrorDetail(
                error=refused.reason,
                next_steps=[
                    "Call `list_tasks` to see the To do keys, then `move_task` again "
                    "with one of them."
                ],
                guide=GUIDE_GETTING_STARTED,
            ).model_dump(),
        ) from None
    page = work_page(session=session, company_id=workspace.id)
    tasks = sorted(page.in_progress + page.to_do, key=lambda t: t.position)
    return McpAnswer[McpTaskList](
        data=McpTaskList(
            tasks=tasks[:25],
            done=page.done[:20],
            sessions=page.sessions,
            waiting=page.waiting,
            total=len(tasks),
        ),
        rules=[
            "Reorder only when the person asks; never on your own. The move is recorded "
            "as theirs, with you as the assistant that acted.",
            "A task you hold goes back to To do when you move it: do that when you stop "
            "working on it, such as an issue fix you hand back.",
            "The person's order wins over Connexity's for the tasks they moved; new tasks "
            "fall in by Connexity's order. A task that blocks a moved one comes up with "
            "it. Another assistant's tasks, questions waiting for the person, and "
            "incidents do not move.",
        ],
        next_steps=[
            "Tell the person the new order: what is next now.",
            "Call `get_next_task` when you are ready for your next task.",
        ],
        guide=GUIDE_GETTING_STARTED,
    )


def _step_text(key: str, instruction: str, *, agents: str = "each agent") -> str:
    """One of an onboarding step's instructions, as the assistant reads it."""
    return for_assistant(STEPS_BY_KEY[key].instruction(instruction).text, agents=agents)


@router.get(
    "/workspaces/{workspace_id}/dashboard",
    response_model=McpAnswer[DashboardPublic],
)
def get_dashboard(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    agent_id: uuid.UUID | None = Query(default=None),
    period: Literal["7d", "30d", "90d"] = "30d",
) -> McpAnswer[DashboardPublic]:
    if agent_id is not None:
        _mcp_agent_in(session, workspace, agent_id)
    page = dashboard(
        session=session, company_id=workspace.id, period=period, agent_id=agent_id
    )
    next_steps: list[str] = []
    worst = next(
        (
            a
            for a in page.areas
            if a.status in ("critical", "warning") and a.top_issue_id
        ),
        None,
    )
    if worst is not None:
        next_steps.append(
            f"The worst area is {worst.name} ({worst.status}): its top issue is "
            f"{worst.top_issue_title}; call `get_issue` with issue_id "
            f"{worst.top_issue_id}."
        )
    if page.onboarding is not None:
        next_steps.append(
            "Onboarding is not complete; call `get_next_task` for the next step."
        )
    next_steps.append(NEXT_TASK)
    return McpAnswer[DashboardPublic](
        data=page,
        rules=[
            "Where the workspace stands, the same picture as the Dashboard page: give "
            "every number with its base (calls, agents, period).",
            "A call is failed when a finding fails it, degraded when findings only flag "
            "it; failed_share and degraded_share are of the period's calls.",
            "Latency p50 and p95 are taken over every reply gap in the period (every "
            "time the agent answered the caller); answers says how many.",
            _SCORE_RULE,
            "An area is critical when its findings failed calls, warning when they only "
            "degraded them, healthy only when one of its checks ran on the period's "
            "calls and found nothing, and not_checked otherwise (waits_for says why). "
            "Never call an area healthy before it is checked.",
            "onboarding is present while scan, specs and answers are not all done.",
        ],
        next_steps=next_steps,
        guide=GUIDE_ISSUES,
    )


@router.get(
    "/workspaces/{workspace_id}/readiness",
    response_model=McpAnswer[ReadinessPublic],
)
def get_readiness(
    session: SessionDep, workspace: McpWorkspaceDep
) -> McpAnswer[ReadinessPublic]:
    readiness = crud.get_readiness(
        session=session,
        company_id=workspace.id,
        mcp_url=settings.oauth_default_resource_url,
    )
    state = {step.key: step.state for step in readiness.steps}
    next_steps: list[str] = []
    if state[ReadinessStepKey.VOICE_PLATFORM] != ReadinessStepState.DONE:
        next_steps.append(_step_text(ReadinessStepKey.VOICE_PLATFORM, "connect"))
    added = crud.linked_agents(session=session, company_id=workspace.id)
    to_scan = [agent for agent in added if agent.platform == Platform.RETELL]
    if to_scan and state[ReadinessStepKey.SYNC] != ReadinessStepState.DONE:
        next_steps.append(_step_text(ReadinessStepKey.SYNC, "scan"))
    if state[ReadinessStepKey.SYNC] != ReadinessStepState.DONE and not added:
        if state[ReadinessStepKey.VOICE_PLATFORM] == ReadinessStepState.DONE:
            next_steps.append(_step_text(ReadinessStepKey.SYNC, "add"))
        else:
            next_steps.append(
                "Syncing agents and calls and the first scan come after the voice "
                "platform is connected."
            )
    if state[ReadinessStepKey.FIRST_SCAN] == ReadinessStepState.DONE:
        waiting = agents_needing_specs(session=session, company_id=workspace.id)
        if waiting:
            names = ", ".join(agent.name for agent, _ in waiting[:5])
            more = f" and {len(waiting) - 5} more" if len(waiting) > 5 else ""
            next_steps.append(_step_text(SPECS, "write", agents=f"{names}{more}"))
    waiting = _waiting_step(session, workspace.id)
    if waiting:
        next_steps.append(waiting)
    next_steps.append(
        "Call `get_readiness` again after each step to see what is left, and tell the "
        "person what changed."
    )
    next_steps.append(NEXT_TASK)
    return McpAnswer[ReadinessPublic](
        data=readiness,
        rules=[
            "Readiness is how complete the workspace's setup is; it never changes the "
            "agents' score.",
            "Getting started has four steps; the controls (alerts, spec, backends, "
            "tests, the gate, rollback) come later.",
            "You do the setup; the person gives keys and approves.",
        ],
        next_steps=next_steps,
        guide=GUIDE_READINESS,
    )


@router.post(
    "/workspaces/{workspace_id}/connections",
    response_model=McpAnswer[McpConnection],
)
async def connect_voice_platform(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    body: McpConnectVoicePlatform,
) -> McpAnswer[McpConnection]:
    provider = IntegrationProvider(body.platform.value)
    platform_name = VOICE_PLATFORMS[provider]
    api_key = body.api_key
    status = await voice_platform_key_status(provider, api_key)
    if status == "unreachable":
        raise HTTPException(
            status_code=503,
            detail=McpErrorDetail(
                error=f"{platform_name} could not be reached to check the key",
                next_steps=[
                    "Try `connect_voice_platform` again in a minute with the same key; "
                    "nothing was stored.",
                ],
                guide=GUIDE_CONNECT,
            ).model_dump(),
        )
    if status == "refused":
        raise HTTPException(
            status_code=400,
            detail=McpErrorDetail(
                error=f"{platform_name} refused this API key",
                next_steps=[
                    f"Ask the person to check the key in {KEY_LOCATION[provider]}, "
                    "then call `connect_voice_platform` again with the new key.",
                ],
                guide=GUIDE_CONNECT,
            ).model_dump(),
        )
    integration, replaced = crud.connect_voice_platform(
        session=session,
        company_id=workspace.id,
        provider=provider,
        name=platform_name,
        api_key=api_key,
        user_id=current_user.id,
        via=assistant,
    )
    person = current_user.full_name or current_user.email
    next_steps = [
        "Tell the person the connection is made, naming the workspace"
        + (" and that the earlier key was replaced." if replaced else "."),
        "Call `get_readiness` to see the next step. Choosing which agents to sync "
        "is not available in Connexity yet.",
    ]
    return McpAnswer[McpConnection](
        data=McpConnection(
            platform=platform_name,
            masked_api_key=integration.masked_api_key,
            replaced_earlier_key=replaced,
            connected_by=f"{person} through {assistant}" if assistant else person,
        ),
        rules=[
            "The key is stored encrypted and is never shown again; do not repeat it.",
            f"Connexity only reads from {platform_name}; it never changes agents there.",
            "One connection per platform per workspace; connecting again replaces "
            "the key.",
        ],
        next_steps=next_steps,
        guide=GUIDE_CONNECT,
    )


@router.post(
    "/workspaces/{workspace_id}/agents",
    response_model=McpAnswer[McpAddedAgents],
)
async def add_agents(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    body: McpAddAgents,
) -> McpAnswer[McpAddedAgents]:
    integration = crud.get_platform_integration(
        session=session, company_id=workspace.id, provider=IntegrationProvider.RETELL
    )
    if integration is None:
        raise HTTPException(
            status_code=409,
            detail=McpErrorDetail(
                error="This workspace has no Retell connection",
                next_steps=[
                    "Connect Retell first: ask the person for the API key and call "
                    "`connect_voice_platform`, then call `add_agents` again.",
                ],
                guide=GUIDE_CONNECT,
            ).model_dump(),
        )
    api_key = decrypt(integration.encrypted_api_key)
    try:
        account = {
            agent.agent_id: agent
            for agent in dedupe_retell_agents(await list_retell_agents(api_key))
        }
    except HTTPException:
        if await retell_key_status(api_key) == "refused":
            raise HTTPException(
                status_code=409,
                detail=McpErrorDetail(
                    error="Retell refused the key stored for this workspace",
                    next_steps=[
                        "The key may have been revoked in Retell. Ask the person for "
                        "a new key, call `connect_voice_platform` with it, then call "
                        "`add_agents` again.",
                    ],
                    guide=GUIDE_CONNECT,
                ).model_dump(),
            )
        raise HTTPException(
            status_code=503,
            detail=McpErrorDetail(
                error="Retell could not be reached to check the agent ids",
                next_steps=[
                    "Nothing was added. Call `add_agents` again in a minute with the "
                    "same ids.",
                ],
                guide=GUIDE_CONNECT,
            ).model_dump(),
        )

    added: list[McpAgent] = []
    already: list[McpAgent] = []
    refused: list[McpRefusedAgent] = []
    seen: set[str] = set()
    for wanted in body.agents:
        platform_id = wanted.platform_agent_id
        if platform_id in seen:
            continue
        seen.add(platform_id)
        found = account.get(platform_id)
        if found is None:
            refused.append(
                McpRefusedAgent(
                    platform_agent_id=platform_id,
                    reason="Not an agent in the connected Retell account",
                )
            )
            continue
        agent, is_new = crud.add_platform_agent(
            session=session,
            company_id=workspace.id,
            integration=integration,
            platform=Platform.RETELL,
            platform_agent_id=platform_id,
            name=wanted.name or found.agent_name or platform_id,
            platform_agent_name=found.agent_name,
            created_by=current_user.id,
        )
        (added if is_new else already).append(_mcp_agent(agent))

    next_steps = []
    if refused:
        next_steps.append(
            "Check the refused ids against Retell and ask the person before adding "
            "them again; they are not in the account connected to this workspace."
        )
    next_steps += [
        "Tell the person which agents were added to this workspace.",
        f"Call `scan_calls` until it says finished to bring in the last {SCAN_DAYS} "
        "days of these agents' calls. New calls arrive on their own within about a "
        "minute; nothing needs setting in Retell.",
        "Optional, only where an added agent's webhook in Retell is empty: setting it "
        f"to {webhook_address(integration.id)} brings calls in seconds after they end. "
        "Never replace a webhook that is already set; the customer may use it.",
    ]
    return McpAnswer[McpAddedAgents](
        data=McpAddedAgents(added=added, already_added=already, refused=refused),
        rules=[
            "Only agents added here are synced; one Retell account may hold several "
            "clients' agents, so add only this client's.",
            "Connexity reads from Retell and never changes the agent there.",
            "Adding an agent that is already in the workspace changes nothing.",
            "New calls are pulled from Retell every minute.",
        ],
        next_steps=next_steps,
        guide=GUIDE_CONNECT,
    )


@router.post(
    "/workspaces/{workspace_id}/scan",
    response_model=McpAnswer[McpScanProgress],
)
async def scan_calls(
    session: SessionDep, workspace: McpWorkspaceDep
) -> McpAnswer[McpScanProgress]:
    if not scan_agents(session=session, company_id=workspace.id):
        raise HTTPException(
            status_code=409,
            detail=McpErrorDetail(
                error="This workspace has no added Retell agents to scan",
                next_steps=[
                    "Add this client's agents first with `add_agents`, then call "
                    "`scan_calls`.",
                ],
                guide=GUIDE_READINESS,
            ).model_dump(),
        )
    try:
        progress = await scan_step(session=session, company_id=workspace.id)
    except HTTPException:
        integration = crud.get_platform_integration(
            session=session,
            company_id=workspace.id,
            provider=IntegrationProvider.RETELL,
        )
        if (
            integration is not None
            and await retell_key_status(decrypt(integration.encrypted_api_key))
            == "refused"
        ):
            raise HTTPException(
                status_code=409,
                detail=McpErrorDetail(
                    error="Retell refused the key stored for this workspace",
                    next_steps=[
                        "The key may have been revoked in Retell. Ask the person for "
                        "a new key, call `connect_voice_platform` with it, then call "
                        "`scan_calls` again; it carries on where it stopped.",
                    ],
                    guide=GUIDE_CONNECT,
                ).model_dump(),
            )
        raise HTTPException(
            status_code=503,
            detail=McpErrorDetail(
                error="Retell could not be reached during the scan",
                next_steps=[
                    "Calls stored so far are kept. Call `scan_calls` again in a "
                    "minute; it carries on where it stopped.",
                ],
                guide=GUIDE_READINESS,
            ).model_dump(),
        )

    stored = sum(agent.stored for agent in progress.agents)
    total = sum(agent.total or 0 for agent in progress.agents)
    if progress.finished:
        next_steps = [
            "Tell the person the first scan is finished: "
            f"{stored:,} call{'' if stored == 1 else 's'} from {len(progress.agents)} "
            f"agent{'' if len(progress.agents) == 1 else 's'} are in Connexity.",
        ]
        if progress.calls_without_versions:
            next_steps.append(
                f"{progress.calls_without_versions:,} calls have no resolved agent "
                "version: Retell no longer has the version that served them. Mention "
                "it; nothing needs doing."
            )
        next_steps.append("Call `get_readiness` to see the next step.")
        next_steps.append(NEXT_TASK)
    else:
        next_steps = [
            f"Call `scan_calls` again: {stored:,} of {total:,} calls stored so far. "
            "Keep calling it until it says finished.",
        ]
    return McpAnswer[McpScanProgress](
        data=progress,
        rules=[
            f"The first scan brings in each added agent's calls from the last "
            f"{SCAN_DAYS} days; later calls arrive by webhook.",
            "Each call does up to about a minute of work and carries on where the last "
            "one stopped; calls already stored are skipped.",
            "Connexity only reads from Retell; it never changes the agents there.",
        ],
        next_steps=next_steps,
        guide=GUIDE_READINESS,
    )


# ── Scenarios ─────────────────────────────────────────────────────

_SCENARIO_RULES = [
    "A scenario is a stage, not a test: it has no pass or fail of its own. A run "
    "judges only the rules it lists: Passed, Failed or Didn't come up.",
    "Every scenario lists one or more rules of the agent's latest spec, by key. "
    "Something no rule covers is a gap in the spec: add the rule (`write_spec`) or "
    "raise a clarification before writing the scenario.",
    "Scenarios need no approval: write them yourself. A person who disagrees asks you "
    "to change one.",
    "Keep what the caller knows apart from the agent's variables. Fake tool results "
    "and every value use invented data, never a real caller's.",
    "Connexity never writes scenarios; you do. The gate runs every scenario; sets are "
    "for your own runs.",
]


def _scenario_refused(refused: ScenarioRefused, retry: str) -> HTTPException:
    more = len(refused.problems) - 20
    return HTTPException(
        status_code=422,
        detail=McpErrorDetail(
            error=refused.error,
            next_steps=[
                *refused.problems[:20],
                *([f"… and {more} more problems like these."] if more > 0 else []),
                retry,
            ],
            guide=GUIDE_SCENARIOS,
        ).model_dump(),
    )


@router.post(
    "/workspaces/{workspace_id}/agents/{agent_id}/scenarios",
    response_model=McpAnswer[McpWrittenScenarios],
)
def write_agent_scenarios(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    agent_id: uuid.UUID,
    body: McpWriteScenarios,
) -> McpAnswer[McpWrittenScenarios]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    try:
        written = write_scenarios(
            session=session,
            agent=agent,
            drafts=[
                ScenarioDraft(
                    id=s.id,
                    archive=s.archive,
                    name=s.name,
                    description=s.description,
                    caller=s.caller,
                    caller_goal=s.caller_goal,
                    caller_behaviour=s.caller_behaviour,
                    caller_knows=s.caller_knows,
                    agent_variables=s.agent_variables,
                    first_turn=s.first_turn,
                    first_message=s.first_message,
                    fake_tool_results=[
                        FakeToolDraft(
                            tool=f.tool, arguments=f.arguments, result=f.result
                        )
                        for f in s.fake_tool_results
                    ],
                    rules=list(s.rules),
                    from_call_id=s.from_call_id,
                )
                for s in body.scenarios
            ],
        )
    except ScenarioRefused as refused:
        raise _scenario_refused(
            refused, "Fix these and call `write_scenarios` again; nothing was stored."
        ) from None
    spec = spec_answer(session=session, agent=agent)
    keys = crud_scenario.rules_of(
        session=session, test_case_ids=[s.id for s in written.stored]
    )
    steps = []
    if written.stored:
        steps.append(
            "Put them in a set with `write_scenario_set` when you will run them "
            'together, such as a small "smoke" set over the critical rules.'
        )
    if written.unlisted_critical:
        first = ", ".join(f"'{r.key}'" for r in written.unlisted_critical[:5])
        steps.append(
            f"{len(written.unlisted_critical)} critical "
            f"{'rule still has' if len(written.unlisted_critical) == 1 else 'rules still have'} "
            f"no scenario: {first}. Write scenarios for them."
        )
    elif spec is not None and (more := _scenario_step(spec, agent.id)):
        steps.append(more)
    steps.append(
        "Tell the person in a line what you wrote; they can ask you to change any of "
        "it."
    )
    steps.append(NEXT_TASK)
    return McpAnswer[McpWrittenScenarios](
        data=McpWrittenScenarios(
            scenarios=[
                scenario_public(s, keys.get(s.id, []), written.rules)
                for s in written.stored
            ],
            archived=written.archived,
        ),
        rules=_SCENARIO_RULES,
        next_steps=steps,
        guide=GUIDE_SCENARIOS,
    )


@router.get(
    "/workspaces/{workspace_id}/agents/{agent_id}/scenarios",
    response_model=McpAnswer[ScenarioListPublic],
)
def list_agent_scenarios(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    agent_id: uuid.UUID,
    rule_key: str | None = Query(default=None, max_length=64),
    set_name: str | None = Query(default=None, alias="set", max_length=255),
    cursor: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
) -> McpAnswer[ScenarioListPublic]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    offset = _decode_cursor(cursor)
    found = list_scenarios(
        session=session,
        agent=agent,
        rule_key=rule_key,
        set_name=set_name,
        offset=offset,
        limit=limit,
    )
    if found is None:
        raise HTTPException(
            status_code=404,
            detail=McpErrorDetail(
                error=f"The agent has no set named '{set_name}'",
                next_steps=["Call `list_scenarios` without `set`; it lists the sets."],
                guide=GUIDE_SCENARIOS,
            ).model_dump(),
        )
    answer, more = found
    answer.next_cursor = _encode_cursor(offset + limit) if more else None
    counts = answer.counts
    steps = []
    if more:
        steps.append(
            "Call `list_scenarios` again with `cursor` set to `next_cursor` for the next "
            "page."
        )
    if counts.listing_gone_rules:
        steps.append(
            f"{counts.listing_gone_rules} "
            f"{'scenario lists' if counts.listing_gone_rules == 1 else 'scenarios list'} "
            "a rule the latest spec no longer has (`gone`): rewrite each with the "
            "spec's keys, or archive it, with `write_scenarios`."
        )
    if counts.critical_unlisted:
        steps.append(
            f"{counts.critical_unlisted} critical "
            f"{'rule has' if counts.critical_unlisted == 1 else 'rules have'} no "
            "scenario (first in `unlisted_rules`): write scenarios for them with "
            "`write_scenarios`."
        )
    elif counts.rules_listed < counts.rules:
        steps.append(
            f"{counts.rules - counts.rules_listed} of {counts.rules} rules have no "
            "scenario (`unlisted_rules`); write scenarios for them with "
            "`write_scenarios`."
        )
    return McpAnswer[ScenarioListPublic](
        data=answer, rules=_SCENARIO_RULES, next_steps=steps, guide=GUIDE_SCENARIOS
    )


@router.post(
    "/workspaces/{workspace_id}/agents/{agent_id}/scenario-sets",
    response_model=McpAnswer[ScenarioSetPublic | None],
)
def write_agent_scenario_set(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    agent_id: uuid.UUID,
    body: McpWriteScenarioSet,
) -> McpAnswer[ScenarioSetPublic | None]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    try:
        config = write_scenario_set(
            session=session,
            agent=agent,
            name=body.name,
            scenario_ids=body.scenario_ids,
            description=body.description,
        )
    except ScenarioRefused as refused:
        raise _scenario_refused(
            refused, "Fix these and call `write_scenario_set` again; nothing changed."
        ) from None
    if config is None:
        return McpAnswer[ScenarioSetPublic | None](
            data=None,
            rules=_SCENARIO_RULES,
            next_steps=[f"The set '{body.name.strip()}' is archived.", NEXT_TASK],
            guide=GUIDE_SCENARIOS,
        )
    ids = crud_scenario.members(session=session, set_ids=[config.id])[config.id]
    return McpAnswer[ScenarioSetPublic | None](
        data=ScenarioSetPublic(
            id=config.id,
            name=config.name,
            description=config.description,
            scenario_ids=ids,
        ),
        rules=_SCENARIO_RULES,
        next_steps=[
            f"The set '{config.name}' has {len(ids)} "
            f"{'scenario' if len(ids) == 1 else 'scenarios'}. Run it with "
            f"`run_scenarios` (set '{config.name}', agent_id {agent.id}) while you work "
            "on a change; the gate always runs every scenario.",
            NEXT_TASK,
        ],
        guide=GUIDE_SCENARIOS,
    )


_TEST_RUN_RULES = [
    "A run judges only the rules each scenario lists: Passed, Failed or Didn't come up. "
    "Didn't come up is not counted. A scenario has no pass or fail of its own.",
    "Every tool is faked: the scenario's fake results first, and every other tool "
    "answers that it is not available in this test. No real tool runs. A hang-up or "
    "a transfer ends the conversation there, as on a real call.",
    f"A conversation ends when the agent hangs up or after {MAX_AGENT_REPLIES} agent "
    "replies, and is judged on what was said. One still going after "
    f"{CONVERSATION_CAP_MS // 60000} minutes is stopped as an error.",
    "A rule that both passed and failed across repeats is flaky. A flaky critical rule "
    "counts as failed.",
    "Code checks run on every simulated call. Their findings never count as production "
    "issues; checks that need timing or a recording are skipped in text.",
    "Only a full run (`all`, every scenario) decides a version's verdict: Verified "
    "when every spec rule was checked and nothing critical was found, Failed on a "
    "critical rule or a critical code check, Partially tested when some rule was not "
    "checked, Not verified without one. A run of a set or a pick is on demand and "
    "never changes it.",
    "A run counts rules, each once: Failed when any repeat failed it, Didn't come up "
    "when no judged repeat reached it. Calls that stopped with an error count in no "
    "column; a run no judge read has no result.",
    "Verified belongs to the content that passed: a version is judged by the latest "
    "full run of what it does now (its newest run's content), under any version "
    "number (`same_content`). A version edited after its full run is not verified "
    "until a new full run (`edited_since`).",
    "Without `version`, results follow the newest tested version, live or not; `live` "
    "gives the live version's state beside it. Every run stores the version it "
    "tested.",
    "Run a set or a pick while working on a change; run every scenario to verify a "
    "version.",
]


def _run_refused(refused: RunRefused) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail=McpErrorDetail(
            error=refused.error,
            next_steps=[*refused.problems, "Nothing was started."],
            guide=GUIDE_SCENARIOS,
        ).model_dump(),
    )


@router.post(
    "/workspaces/{workspace_id}/agents/{agent_id}/test-runs",
    response_model=McpAnswer[McpStartedRun],
)
async def run_agent_scenarios(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    agent_id: uuid.UUID,
    body: McpRunScenarios,
) -> McpAnswer[McpStartedRun]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    try:
        tested = await version_to_test(session=session, agent=agent, asked=body.version)
        run = start_run(
            session=session,
            agent=agent,
            user_id=current_user.id,
            request=RunRequest(
                set_name=body.set,
                scenario_ids=body.scenario_ids,
                all=body.all,
                repeats=body.repeats,
                version=tested.number,
                fingerprint=tested.fingerprint,
                assistant_name=assistant,
                session_name=(body.session or "").strip() or None,
            ),
        )
    except RunRefused as refused:
        raise _run_refused(refused) from None
    calls = len(crud_test_run.calls_of_runs(session=session, run_ids=[run.id])[run.id])
    launch(run.id)
    return McpAnswer[McpStartedRun](
        data=McpStartedRun(run_id=run.id, calls=calls),
        rules=_TEST_RUN_RULES,
        next_steps=[
            f"The run makes {calls} simulated "
            f"{'call' if calls == 1 else 'calls'} in the background. Call "
            f"`get_test_runs` with run_id {run.id} until its status is completed.",
            "It is a full run: when it completes, it decides the version's verdict."
            if body.all
            else "It is an on-demand run: it never changes the version's verdict. Run "
            "every scenario (`all`) to verify the version.",
            "Meanwhile, carry on with other work.",
        ],
        guide=GUIDE_SCENARIOS,
    )


def _run_steps(
    run: TestRunDetailPublic, more: bool, offset: int, limit: int
) -> list[str]:
    counts = run.counts
    if run.status in (RunStatus.PENDING, RunStatus.RUNNING):
        return [
            f"Still running: {counts.finished} of {counts.calls} simulated calls "
            f"finished. Call `get_test_runs` with run_id {run.id} again."
        ]
    if run.totals is not None and not run.totals.judged_calls:
        return [
            f"No result: every one of its {counts.calls} simulated calls stopped with "
            "an error before a judge read it, so it counts nothing. Read the calls' "
            "`error`, fix the cause, then run again with `run_scenarios`."
        ]
    if run.status is RunStatus.FAILED:
        return [
            f"The run stopped: {run.status_detail or 'unknown reason'}. Fix that and "
            "start it again with `run_scenarios`."
        ]
    steps: list[str] = []
    if counts.critical_failed:
        steps.append(
            f"{counts.critical_failed} critical "
            f"{'rule' if counts.critical_failed == 1 else 'rules'} failed (first in "
            "`rules`). Read the failing calls' reasons, then fix the agent or, if the "
            "scenario is wrong, the scenario (`write_scenarios`)."
        )
    if counts.rules_failed > counts.critical_failed:
        other = counts.rules_failed - counts.critical_failed
        steps.append(
            f"{other} other {'rule' if other == 1 else 'rules'} failed. Tell the person "
            "what failed and what you suggest; they decide what changes."
        )
    if counts.flaky:
        steps.append(
            f"{counts.flaky} {'rule is' if counts.flaky == 1 else 'rules are'} flaky "
            "(`flaky`): it passed in some repeats and failed in others. Look at both."
        )
    defaults = sorted({tool for call in run.calls for tool in call.default_fakes})
    if defaults:
        steps.append(
            "These tools answered with the default fake because a scenario did not "
            f"fake them: {', '.join(defaults)}. Add fake results with `write_scenarios`."
        )
    if counts.findings:
        steps.append(
            f"Code checks found {counts.findings} "
            f"{'problem' if counts.findings == 1 else 'problems'} (`checks`); they do "
            "not count as production issues."
        )
    if counts.errors:
        steps.append(
            f"{counts.errors} simulated {'call' if counts.errors == 1 else 'calls'} "
            "ended in an error (`error`) and gave no verdicts; run those scenarios again."
        )
    if run.dropped_rules:
        steps.append(
            "Some scenarios list rules the run's spec no longer has, which were not "
            f"judged: {', '.join(run.dropped_rules[:10])}. Rewrite them with "
            "`write_scenarios`."
        )
    if not steps:
        steps.append("Every judged rule passed, with no code-check findings.")
    steps.append(
        "For the version's verdict, from its latest full run, call `get_test_runs` without "
        f"`run_id`{f' and version {run.platform_version}' if run.platform_version else ''}."
    )
    if more:
        steps.append(
            "Call `get_test_runs` again with `cursor` set to `next_cursor` for the next "
            f"simulated calls (from {offset + limit + 1})."
        )
    return steps


def _version_name(results: VersionResultsPublic) -> str:
    return f"Version {results.version}" if results.version else "The latest version"


def _coverage_steps(results: VersionResultsPublic) -> list[str]:
    coverage = results.coverage
    if coverage is None or not coverage.uncovered:
        return []
    critical = [u for u in coverage.uncovered if u.critical]
    lead = (
        f"Coverage is {coverage.pct}%: {coverage.covered} of the spec's "
        f"{coverage.rules} rules have a scenario."
    )
    if not critical:
        return [f"{lead} Write scenarios for the rest (`coverage.uncovered`)."]
    keys = ", ".join(u.key for u in critical[:5])
    return [
        f"{lead} {len(critical)} critical "
        f"{'rule has' if len(critical) == 1 else 'rules have'} none ({keys}): write "
        "scenarios that list them (`write_scenarios`), then run every scenario."
    ]


def _stopped_steps(results: VersionResultsPublic) -> list[str]:
    stopped = results.stopped
    if stopped is None:
        return []
    many = stopped.calls != 1
    return [
        f"{stopped.calls} simulated {'calls' if many else 'call'} of the full run "
        f'stopped with an error and gave no verdicts, most often "{stopped.reason}". '
        "Rules they never reached are not checked. Open run "
        f"{stopped.run_id} with `get_test_runs` to see each call's error."
    ]


def _verdict_steps(results: VersionResultsPublic) -> list[str]:
    name = _version_name(results)
    full = results.full_run
    when = (
        f" (run {full.id}, {full.completed_at:%d %b %H:%M})"
        if full is not None and full.completed_at
        else ""
    )
    if results.verdict is VersionVerdict.NOT_VERIFIED:
        earlier = (
            f" Version {results.last_verified.version} was verified "
            f"{results.last_verified.at:%d %b}."
            if results.last_verified
            else ""
        )
        if full is not None:
            return [
                f"{name} is not verified: its full run{when} judged no rule.{earlier} "
                "Fix why its calls stopped, then run every scenario again "
                "(`run_scenarios` with `all`)."
            ]
        if results.edited_since is not None:
            return [
                f"{name} is not verified: it was edited after its full run of "
                f"{results.edited_since:%d %b %H:%M}, so that run no longer counts. Run "
                "every scenario again (`run_scenarios` with `all`) to verify what it "
                "does now."
            ]
        return [
            f"{name} is not verified: it has no completed full run.{earlier} Run every "
            "scenario on it (`run_scenarios` with `all`): only a full run verifies a "
            "version."
        ]
    by = "its full run"
    if results.same_content is not None:
        same = results.same_content
        by = f"version {same.version}'s full run of the same content"
        when = f" (run {same.run_id}, {same.at:%d %b %H:%M})"
    if results.verdict is VersionVerdict.FAILED:
        why = []
        if results.critical_failed:
            why.append(
                f"critical {'rule' if len(results.critical_failed) == 1 else 'rules'} "
                f"{', '.join(results.critical_failed)} failed"
            )
        if results.critical_checks:
            why.append(
                f"critical code {'check' if len(results.critical_checks) == 1 else 'checks'} "
                f"{', '.join(results.critical_checks)} found problems"
            )
        return [
            f"{name} failed in {by}{when}: {'; '.join(why)}.",
            "For each, open a failing simulated call (`get_test_runs` with the run's "
            "`run_id`) and read the reason. If the scenario is wrong, fix it with "
            "`write_scenarios`; otherwise tell the person what failed and what you "
            "suggest, with the call's link. Connexity never changes the agent.",
            "After the agent is changed, run every scenario again with `run_scenarios`.",
        ]
    if results.verdict is VersionVerdict.PARTIAL:
        keys = ", ".join(u.key for u in results.unchecked[:5])
        return [
            f"{name} is partially tested: {by}{when} found nothing critical, "
            f"but {len(results.unchecked)} "
            f"{'rule was' if len(results.unchecked) == 1 else 'rules were'} not checked "
            f"({keys}; `unchecked` says why). Write scenarios that reach them, or "
            "rewrite the ones that list them but never got there, then run every "
            "scenario again."
        ]
    failed = sum(1 for r in results.rules if r.failed)
    return [
        f"{name} is verified by {by}{when}: every rule checked, nothing "
        "critical found"
        + (
            f"; {failed} non-critical {'rule' if failed == 1 else 'rules'} failed, so "
            "tell the person which."
            if failed
            else "."
        )
    ]


def _live_steps(results: VersionResultsPublic) -> list[str]:
    live = results.live
    if live is None:
        return []
    state = (
        f"verified {live.at:%d %b}"
        if live.verdict is VersionVerdict.VERIFIED and live.at
        else live.verdict.value.replace("_", " ")
    )
    return [
        f"{_version_name(results)} is not the live version. The live version is "
        f"{live.version}, {state}; call `get_test_runs` with version {live.version} "
        "for its runs."
    ]


def _results_steps(results: VersionResultsPublic) -> list[str]:
    return [
        *_verdict_steps(results),
        *_live_steps(results),
        *_stopped_steps(results),
        *_coverage_steps(results),
    ]


@router.get(
    "/workspaces/{workspace_id}/agents/{agent_id}/test-runs",
    response_model=McpAnswer[McpTestRuns],
)
def get_agent_test_runs(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    agent_id: uuid.UUID,
    run_id: uuid.UUID | None = Query(default=None),
    version: str | None = Query(default=None, max_length=64),
    cursor: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
) -> McpAnswer[McpTestRuns]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    offset = _decode_cursor(cursor)
    if run_id is None:
        results = version_results(session=session, agent=agent, version=version)
        if version is not None and results is None:
            raise HTTPException(
                status_code=404,
                detail=McpErrorDetail(
                    error=f"No run tested version {version} of this agent",
                    next_steps=[
                        "Call `get_test_runs` without `version` for the newest tested "
                        "version, or run the scenarios on it with `run_scenarios`."
                    ],
                    guide=GUIDE_SCENARIOS,
                ).model_dump(),
            )
        runs, more = list_runs(session=session, agent=agent, offset=offset, limit=limit)
        assert results is not None  # without `version`, there are always results
        steps = [
            *_results_steps(results),
            "Call `get_test_runs` with a `run_id` for its simulated calls, each with a "
            "link (`url`) you can give the person.",
        ]
        if more:
            steps.append(
                "Call `get_test_runs` again with `cursor` set to `next_cursor` for "
                "older runs."
            )
        return McpAnswer[McpTestRuns](
            data=McpTestRuns(results=results, runs=runs),
            rules=_TEST_RUN_RULES,
            next_steps=steps,
            guide=GUIDE_SCENARIOS,
            next_cursor=_encode_cursor(offset + limit) if more else None,
        )
    run = crud_test_run.run_of_agent(session=session, agent_id=agent.id, run_id=run_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=McpErrorDetail(
                error="The agent has no run with this id",
                next_steps=[
                    "Call `get_test_runs` without `run_id`; it lists the runs."
                ],
                guide=GUIDE_SCENARIOS,
            ).model_dump(),
        )
    detail, more = run_detail(session=session, run=run, offset=offset, limit=limit)
    return McpAnswer[McpTestRuns](
        data=McpTestRuns(run=detail),
        rules=_TEST_RUN_RULES,
        next_steps=_run_steps(detail, more, offset, limit),
        guide=GUIDE_SCENARIOS,
        next_cursor=_encode_cursor(offset + limit) if more else None,
    )


_FEEDBACK_RULES = [
    "Report Connexity's own problems here: a Connexity tool that fails, answers "
    "something another answer contradicts, or cannot do what the work needs. A problem "
    "in the person's own agent is an issue, not feedback.",
    "Never put caller data in a report (no transcripts, phone numbers or names) and "
    "never a secret: describe what happened and give ids instead.",
    "Report each problem once, after one retry, without asking the person first.",
    f"A workspace sends at most {FEEDBACK_DAILY_CAP} reports a day.",
]


@router.post(
    "/workspaces/{workspace_id}/feedback",
    response_model=McpAnswer[McpFeedbackSent],
)
async def send_feedback(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    body: McpSendFeedback,
) -> McpAnswer[McpFeedbackSent]:
    try:
        report = store_report(
            session=session,
            company_id=workspace.id,
            person=current_user,
            report=FeedbackIn(
                kind=body.kind,
                title=body.title,
                what_happened=body.what_happened,
                wanted=body.wanted,
                tool=body.tool,
                error=body.error,
                ids=body.ids,
                assistant_name=assistant,
                session_name=(body.session or "").strip() or None,
            ),
        )
    except FeedbackRefused as refused:
        raise HTTPException(
            status_code=422,
            detail=McpErrorDetail(
                error=str(refused),
                next_steps=["Nothing was stored. Fix it and send it again."],
                guide=GUIDE_FEEDBACK,
            ).model_dump(),
        ) from None
    post_in_background(report.id)
    return McpAnswer[McpFeedbackSent](
        data=McpFeedbackSent(report_id=report.id),
        rules=_FEEDBACK_RULES,
        next_steps=[
            f"Reported as {report.id}; the Connexity team reads every report.",
            "Tell the person in one sentence that you reported it, then carry on with "
            "the work, around the problem if you can.",
        ],
        guide=GUIDE_FEEDBACK,
    )
