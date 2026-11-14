"""Backend routes behind the MCP server's tools.

Every route answers in the standard shape (`McpAnswer`): the facts, the rules that
apply, numbered next steps and a guide. Every route except `/mcp/workspaces` is scoped
to a workspace in its path, resolved by `require_mcp_workspace`.
"""

import base64
import binascii
import uuid
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
from app.crud.call_list import CallFilters
from app.crud.issue_list import calls_by_agent, period_start
from app.crud.latency import agent_latencies
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
from app.models.agent_page import AgentPagePublic
from app.models.check import Issue
from app.models.enums import CallCheckStatus, IssueState
from app.models.issue_list import IssuePeriod, IssueStatusFilter
from app.models.issue_page import IssuePagePublic
from app.models.mcp import (
    GUIDE_CALLS,
    GUIDE_CATEGORIES,
    GUIDE_CONNECT,
    GUIDE_GETTING_STARTED,
    GUIDE_ISSUES,
    GUIDE_READINESS,
    GUIDE_SPEC,
    GUIDE_WORKSPACES,
    McpAddAgents,
    McpAddedAgents,
    McpAgent,
    McpAnswer,
    McpArchiveIssue,
    McpCalls,
    McpConnection,
    McpConnectVoicePlatform,
    McpErrorDetail,
    McpIssues,
    McpRefusedAgent,
    McpScanProgress,
    McpUnarchiveIssue,
    McpWorkspace,
    McpWriteSpec,
)
from app.models.spec import SpecPublic, SpecWrittenPublic
from app.services.agent_list import agent_types
from app.services.agent_page import agent_page
from app.services.call_list import workspace_calls
from app.services.call_screen import call_screen
from app.services.connections import (
    KEY_LOCATION,
    VOICE_PLATFORMS,
    voice_platform_key_status,
    webhook_address,
)
from app.services.first_scan import SCAN_DAYS, scan_agents, scan_step
from app.services.issue_list import IssueFilters, workspace_issues
from app.services.issue_page import issue_page
from app.services.retell import (
    dedupe_retell_agents,
    list_retell_agents,
    retell_key_status,
)
from app.services.spec import (
    RuleDraft,
    SpecRefused,
    agents_needing_specs,
    spec_answer,
    spec_state,
    write_agent_spec,
)

router = APIRouter(
    prefix="/mcp",
    tags=["mcp"],
    dependencies=[Depends(require_mcp_user)],
)

_CURSOR_PREFIX = "o:"
_CURSOR_MAX_OFFSET = 1_000_000_000


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
    return McpAnswer[list[McpWorkspace]](
        data=[McpWorkspace(id=w.id, name=w.name) for w in workspaces],
        rules=[
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
    return McpAnswer[McpCalls](
        data=McpCalls(tiles=page.tiles, calls=page.data),
        rules=[
            "Calls come newest first; the tiles count every call matching the "
            "filters in the period, whatever the result filter.",
            "Callers are shown as their last four digits only; never ask Connexity or "
            "repeat a full number.",
            "A result is failed when a finding fails the call, degraded when one only "
            "flags it, clean when checks ran and found nothing, unchecked otherwise. "
            "Say whether the worst finding was found by a rule or a model.",
            "Findings of archived issues are left out of every call's result, worst "
            "finding and findings, until the issue is unarchived.",
            "With issue_id, only the calls that issue was found on are listed, each with "
            "its moment: when it first happened in the call and how many times.",
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
            "Worst first: open or reopened Critical issues and reopened ones, then the "
            "other open ones, then by calls affected in the period.",
            "status defaults to open, which includes reopened. Open and reopened issues "
            "show whatever the period; a resolved one only if it was resolved in the "
            "period; archived ones always.",
            "The tiles follow agent_id and the period only, never the search or the "
            "other filters.",
            "Say how each issue was found: found_by rule means deterministic code over "
            "the call; model means a classifier or judge.",
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
    "the last 30 days), and say how it was found: found_by rule means deterministic "
    "code over the call; model means a classifier or judge.",
    "An affected call's moment is when the issue first happened in it, and how many "
    "times; open the call with `get_call` to see it.",
    "Archiving is the person's decision. Before `archive_issue` or `unarchive_issue`, "
    "say which issue, its size and the duration, and wait for the person's yes; put "
    "their words in the reason.",
    "While archived, the issue is hidden on every call, including earlier ones, and "
    "counts for nothing; until_spike brings it back as reopened when it starts "
    "happening twice as often.",
]


def _issue_answer(
    session: SessionDep, issue: Issue, next_steps: list[str]
) -> McpAnswer[IssuePagePublic]:
    page = issue_page(
        session=session,
        issue=issue,
        summary=crud.summarise_issue(session=session, issue=issue),
    )
    if page.tiles.calls_affected:
        next_steps.append(
            f"Call `list_calls` with issue_id {issue.id} for every call it was found on."
        )
    return McpAnswer[IssuePagePublic](
        data=page, rules=_ISSUE_RULES, next_steps=next_steps, guide=GUIDE_ISSUES
    )


@router.get(
    "/workspaces/{workspace_id}/issues/{issue_id}",
    response_model=McpAnswer[IssuePagePublic],
)
def get_issue(
    session: SessionDep, workspace: McpWorkspaceDep, issue_id: uuid.UUID
) -> McpAnswer[IssuePagePublic]:
    issue = _mcp_issue(session, workspace, issue_id)
    next_steps = []
    if issue.state is not IssueState.ARCHIVED:
        next_steps.append(
            "If the person decides nobody will fix it, ask them, then call "
            "`archive_issue` with their reason."
        )
    return _issue_answer(session, issue, next_steps)


@router.post(
    "/workspaces/{workspace_id}/issues/{issue_id}/archive",
    response_model=McpAnswer[IssuePagePublic],
)
def archive_issue(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    issue_id: uuid.UUID,
    body: McpArchiveIssue,
) -> McpAnswer[IssuePagePublic]:
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
            "`unarchive_issue` brings it back."
        ],
    )


@router.post(
    "/workspaces/{workspace_id}/issues/{issue_id}/unarchive",
    response_model=McpAnswer[IssuePagePublic],
)
def unarchive_issue(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    current_user: McpCurrentUser,
    assistant: McpAssistantName,
    issue_id: uuid.UUID,
    body: McpUnarchiveIssue,
) -> McpAnswer[IssuePagePublic]:
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
    latency = agent_latencies(
        session=session, agent_ids=ids, since=period_start(period)
    )
    calls = calls_by_agent(
        session=session, company_id=workspace.id, since=period_start(period)
    )
    data = []
    for agent in agents:
        row = _mcp_agent(agent)
        row.type = types.get(agent.id)
        row.calls = calls.get(agent.id, 0)
        row.latency_seconds = latency.get(agent.id)
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
    "Keep a rule across versions by passing its key; a kept rule without its key reads "
    "as dropped and added again.",
    "Rules are never edited: every `write_spec` is a new version, and earlier versions "
    "stay as they were.",
]


def _spec_steps(answer: SpecPublic) -> list[str]:
    steps = []
    if answer.current_agent_version is None:
        steps.append(
            "The agent has no calls yet, so its version is not known; write its spec "
            "after its first call."
        )
    elif answer.state == "none":
        steps.append(
            "Write the spec: call `get_spec` with include_prompt for the prompt "
            "Connexity recorded, then `write_spec`."
        )
    elif answer.state == "needs_review":
        steps.append(
            f"The agent moved to version {answer.current_agent_version}; Connexity "
            "copied the previous spec to it. Compare the prompts, keep what holds (with "
            "keys), write what changed with `write_spec`, and list to the person what the "
            "change leaves unsettled."
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
    include_prompt: bool = False,
) -> McpAnswer[SpecPublic]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    answer = spec_answer(
        session=session, agent=agent, version=version, include_prompt=include_prompt
    )
    if answer is None:
        raise HTTPException(
            status_code=404,
            detail=McpErrorDetail(
                error=f"The agent has no spec version {version}",
                next_steps=["Call `get_spec` without a version for the latest."],
                guide=GUIDE_SPEC,
            ).model_dump(),
        )
    steps = _spec_steps(answer)
    if include_prompt and answer.current_agent_version and answer.prompt is None:
        steps.append(
            "Connexity has no recorded prompt for this version; read it from the voice "
            "platform. Quotes will be stored without being checked."
        )
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
                )
                for r in body.rules
            ],
            author=current_user,
            assistant_name=assistant or "your assistant",
        )
    except SpecRefused as refused:
        raise HTTPException(
            status_code=422,
            detail=McpErrorDetail(
                error=refused.error,
                next_steps=[
                    *refused.problems[:20],
                    *(
                        [
                            f"… and {len(refused.problems) - 20} more problems like these."
                        ]
                        if len(refused.problems) > 20
                        else []
                    ),
                    "Fix these and call `write_spec` again with every rule; nothing "
                    "was stored.",
                ],
                guide=GUIDE_SPEC,
            ).model_dump(),
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
    steps.append(
        "Tell the person the spec is written, and list the behaviour you have seen on "
        "calls that the prompt does not settle, as questions for them."
    )
    return McpAnswer[SpecWrittenPublic](
        data=written, rules=_SPEC_RULES, next_steps=steps, guide=GUIDE_SPEC
    )


_LATENCY_RULE = (
    "latency_seconds is a basic measure from each call's turns: the median time from "
    "the caller finishing to the agent starting to answer, averaged across calls. "
    "Turns where the agent starts before the caller finishes are not counted."
)


@router.get(
    "/workspaces/{workspace_id}/agents/{agent_id}",
    response_model=McpAnswer[AgentPagePublic],
)
def get_agent(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    agent_id: uuid.UUID,
    period: Literal["7d", "30d", "90d"] = "30d",
) -> McpAnswer[AgentPagePublic]:
    agent = _mcp_agent_in(session, workspace, agent_id)
    page = agent_page(session=session, agent=agent, period=period)
    next_steps = [
        f"Call `list_calls` with agent_id {agent.id} for its calls, and `list_issues` "
        "with the same for what was found on them."
    ]
    if page.spec != "current" and page.live_version:
        next_steps.append(
            "The agent's spec is missing or needs review: call `get_spec` and "
            "`write_spec`, following connexity://guides/spec."
        )
    return McpAnswer[AgentPagePublic](
        data=page,
        rules=[
            _LATENCY_RULE,
            "live_version is the agent version of its most recent call, and live_since "
            "when the first call on it started.",
            "systems are the n8n workflows its tool calls ran in the period.",
        ],
        next_steps=next_steps,
        guide=GUIDE_GETTING_STARTED,
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
        next_steps.append(
            "Connect the voice platform: ask the person for their Retell API key "
            "(Retell's dashboard, under API Keys), then call `connect_voice_platform` "
            "with it. Do not repeat the key in your reply."
        )
    added = crud.linked_agents(session=session, company_id=workspace.id)
    to_scan = [agent for agent in added if agent.platform == Platform.RETELL]
    if to_scan and state[ReadinessStepKey.SYNC] != ReadinessStepState.DONE:
        next_steps.append(
            f"Bring in the added agents' calls from the last {SCAN_DAYS} days: call "
            "`scan_calls` and keep calling it until it says finished. Tell the person "
            "how far it has got from time to time."
        )
    if state[ReadinessStepKey.SYNC] != ReadinessStepState.DONE and not added:
        if state[ReadinessStepKey.VOICE_PLATFORM] == ReadinessStepState.DONE:
            next_steps.append(
                "The voice platform is connected; do not ask for the key again. Use "
                "your own access to Retell to see its agents and their recent calls, "
                "ask the person which belong to this client, then call `add_agents` "
                "with their Retell agent ids."
            )
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
            next_steps.append(
                f"Write each agent's spec from its prompt: {names}{more}. Read "
                "connexity://guides/spec, then call `get_spec` with include_prompt and "
                "`write_spec`."
            )
    next_steps.append(
        "Call `get_readiness` again after each step to see what is left, and tell the "
        "person what changed."
    )
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
