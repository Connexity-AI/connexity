from __future__ import annotations

import contextlib
from typing import Annotated, Literal
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from mcp.server.auth.routes import build_resource_metadata_url
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.streamable_http import MCP_PROTOCOL_VERSION_HEADER
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.types import ASGIApp, Receive, Scope, Send

from connexity_mcp_server.auth import OidcTokenVerifier
from connexity_mcp_server.client import ConnexityBackendClient
from connexity_mcp_server.config import Settings
from connexity_mcp_server.manifest import Manifest, build_manifest
from connexity_mcp_server.guides import (
    GUIDE_URI_PREFIX,
    GUIDES,
    INSTRUCTIONS,
    read_guide,
)
from connexity_mcp_server.models import (
    InvitePeopleResult,
    ListPeopleResult,
    PrepareWorkspaceDeletionResult,
    RemovePersonResult,
    UpdatePersonResult,
    AddAgentsResult,
    AgentToAdd,
    ConnectVoicePlatformResult,
    CreateWorkspaceResult,
    GetCallResult,
    GetNextTaskResult,
    ListTasksResult,
    GetDashboardResult,
    GetUsageResult,
    GetReadinessResult,
    AgentResult,
    AnswerClarificationsResult,
    AnswerToGive,
    IssueResult,
    ListClarificationsResult,
    QuestionToRaise,
    RaiseClarificationsResult,
    SpecResult,
    ListScenariosResult,
    RunScenariosResult,
    SendFeedbackResult,
    TestRunsResult,
    ScenarioSetResult,
    ScenarioToWrite,
    WriteScenariosResult,
    SpecRuleToWrite,
    ListAgentsResult,
    ListCallsResult,
    ReadCallsResult,
    ListCategoriesResult,
    ListIssuesResult,
    ListWorkspacesResult,
    ScanCallsResult,
)
from connexity_mcp_server.tools import (
    invite_people as _invite_people,
    list_people as _list_people,
    prepare_workspace_deletion as _prepare_workspace_deletion,
    remove_person as _remove_person,
    update_person as _update_person,
    add_agents as _add_agents,
)
from connexity_mcp_server.tools import (
    send_feedback as _send_feedback,
)
from connexity_mcp_server.tools import (
    answer_clarifications as _answer_clarifications,
)
from connexity_mcp_server.tools import (
    list_clarifications as _list_clarifications,
)
from connexity_mcp_server.tools import (
    raise_clarifications as _raise_clarifications,
)
from connexity_mcp_server.tools import (
    connect_voice_platform as _connect_voice_platform,
)
from connexity_mcp_server.tools import (
    create_workspace as _create_workspace,
)
from connexity_mcp_server.tools import (
    get_next_task as _get_next_task,
)
from connexity_mcp_server.tools import (
    list_tasks as _list_tasks,
)
from connexity_mcp_server.tools import (
    move_task as _move_task,
)
from connexity_mcp_server.tools import (
    get_readiness as _get_readiness,
)
from connexity_mcp_server.tools import (
    get_dashboard as _get_dashboard,
    get_usage as _get_usage,
)
from connexity_mcp_server.tools import (
    list_agents as _list_agents,
)
from connexity_mcp_server.tools import (
    list_categories as _list_categories,
)
from connexity_mcp_server.tools import (
    get_call as _get_call,
)
from connexity_mcp_server.tools import (
    list_calls as _list_calls,
    read_calls as _read_calls,
)
from connexity_mcp_server.tools import (
    list_issues as _list_issues,
)
from connexity_mcp_server.tools import (
    get_issue as _get_issue,
)
from connexity_mcp_server.tools import (
    get_spec as _get_spec,
)
from connexity_mcp_server.tools import (
    get_agent as _get_agent,
)
from connexity_mcp_server.tools import (
    write_spec as _write_spec,
)
from connexity_mcp_server.tools import (
    mark_critical_rules as _mark_critical_rules,
)
from connexity_mcp_server.tools import (
    list_scenarios as _list_scenarios,
)
from connexity_mcp_server.tools import (
    write_scenario_set as _write_scenario_set,
)
from connexity_mcp_server.tools import (
    run_scenarios as _run_scenarios,
)
from connexity_mcp_server.tools import (
    get_test_runs as _get_test_runs,
)
from connexity_mcp_server.tools import (
    write_scenarios as _write_scenarios,
)
from connexity_mcp_server.tools import (
    archive_issue as _archive_issue,
)
from connexity_mcp_server.tools import (
    unarchive_issue as _unarchive_issue,
)
from connexity_mcp_server.tools import (
    mark_issue_fixed as _mark_issue_fixed,
)
from connexity_mcp_server.tools import (
    list_workspaces as _list_workspaces,
)
from connexity_mcp_server.tools import (
    scan_calls as _scan_calls,
)

# Inputs every tool shares. Every input has a description: the assistant reads it in
# the tool's schema, and the public contract page shows it (`contract.py`).
WorkspaceId = Annotated[
    str, Field(description="The workspace, from `list_workspaces`.")
]
AgentId = Annotated[str, Field(description="The agent, from `list_agents`.")]
IssueId = Annotated[str, Field(description="The issue, from `list_issues`.")]
Cursor = Annotated[
    str | None,
    Field(description="`next_cursor` from the previous page; leave empty for the first."),
]
Limit = Annotated[int | None, Field(description="Items per page, 1 to 100.")]
# For tools whose page size always has a value (25 by default).
PageSize = Annotated[int, Field(description="Items per page, 1 to 100.")]
Period = Annotated[
    str | None, Field(description="7d, 30d or 90d. Leave empty for 30d.")
]


# Hints assistants read to decide whether to ask the person before a call. Every tool
# acts only inside Connexity (`openWorldHint=False`).
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
CREATES = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
)
# Reads calls from the voice platform into Connexity; repeating it carries on.
SCANS = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
)
# Talks to the agent on its voice platform in simulated calls; every tool is faked.
RUNS = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
)
# Archives or unarchives an issue: a person's decision the assistant makes only with
# their yes. Not destructive (nothing is deleted); repeating it changes nothing.
DECIDES = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
# Removes a person from an agency or cancels an invite: access ends at once.
REMOVES = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False
)
# Reads from the voice platform to check the key; replaces an earlier key.
CONNECTS = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
)


class NormalizeMcpPathMiddleware:
    """Allow both `/mcp` and `/mcp/` to reach the mounted MCP app."""

    def __init__(self, app: ASGIApp, mcp_path: str) -> None:
        self.app = app
        self.mcp_path = mcp_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in {"http", "websocket"} and scope["path"] == self.mcp_path:
            scope = dict(scope)
            scope["path"] = f"{self.mcp_path}/"
            raw_path = scope.get("raw_path")
            if isinstance(raw_path, bytes):
                scope["raw_path"] = f"{self.mcp_path}/".encode()
        await self.app(scope, receive, send)


def build_application(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.require_mcp_oauth()
    backend_client = ConnexityBackendClient(settings)
    token_verifier = OidcTokenVerifier(settings)
    auth_settings = AuthSettings(
        issuer_url=settings.validated_mcp_oauth_issuer_url,
        resource_server_url=settings.validated_mcp_oauth_resource_server_url,
        required_scopes=settings.resolved_mcp_oauth_required_scopes or None,
    )
    mcp_server = FastMCP(
        settings.mcp_server_name,
        instructions=INSTRUCTIONS,
        stateless_http=True,
        json_response=True,
        streamable_http_path="/",
        auth=auth_settings,
        token_verifier=token_verifier,
        transport_security=TransportSecuritySettings(
            allowed_hosts=settings.resolved_allowed_hosts,
            allowed_origins=settings.resolved_allowed_origins,
        ),
    )

    @mcp_server.tool(annotations=READ_ONLY)
    async def list_workspaces() -> ListWorkspacesResult:
        """The workspaces you can reach: one per client, each with its score over
        the last 30 days and its change, the agency it belongs to, and the person's
        role there. Call this first; every other tool takes a `workspace_id` from
        here."""
        return await _list_workspaces(client=backend_client)

    @mcp_server.tool(annotations=CREATES)
    async def create_workspace(
        name: Annotated[str, Field(description="The client's name, as the person gives it.")],
        agency_id: Annotated[
            str | None,
            Field(
                description="The agency to create it in, from a workspace's `agency` "
                "in `list_workspaces`. Leave out unless the person is an Admin of "
                "more than one agency."
            ),
        ] = None,
    ) -> CreateWorkspaceResult:
        """Create a workspace for a new client in the person's agency. Only an Admin
        of the agency can; for anyone else the answer names who to ask. Ask the
        person for the client's name first."""
        return await _create_workspace(
            client=backend_client, name=name, agency_id=agency_id
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def prepare_workspace_deletion(
        workspace_id: WorkspaceId,
    ) -> PrepareWorkspaceDeletionResult:
        """What deleting this workspace would remove (calls, agents, issues,
        connections), whether your person can delete it and who can, and where on the
        web they do it. It deletes nothing, and no tool deletes a workspace: only a
        person does, by typing its name. Call it when the person asks to delete a
        client's workspace or its data."""
        return await _prepare_workspace_deletion(
            client=backend_client, workspace_id=workspace_id
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def list_people(workspace_id: WorkspaceId) -> ListPeopleResult:
        """Who is in the agency this workspace belongs to: each person's role, the
        workspaces they reach, whether they can approve and how many assistants they
        have connected, plus the invites still waiting. Read this before answering who
        has access, and before inviting, changing or removing anyone."""
        return await _list_people(client=backend_client, workspace_id=workspace_id)

    @mcp_server.tool(annotations=CREATES)
    async def invite_people(
        workspace_id: WorkspaceId,
        emails: Annotated[list[str], Field(description="The email addresses to invite, as the person gives them.")],
        role: Annotated[Literal["admin", "member"], Field(description="admin manages people and billing and creates workspaces; member works in their workspaces.")] = "member",
        all_workspaces: Annotated[bool, Field(description="True: they reach every workspace of the agency, also later ones. False: only `workspace_ids`.")] = True,
        workspace_ids: Annotated[list[str] | None, Field(description="The workspaces they reach when `all_workspaces` is false, from `list_people`; at least one.")] = None,
        can_approve: Annotated[bool, Field(description="Whether they may make the critical decisions (archive issues, change checks) in their workspaces.")] = False,
    ) -> InvitePeopleResult:
        """Invite people to the agency by email; each gets a link that works once and
        for 7 days. Only when the person you act for is an admin, and only after they
        said yes to these addresses, role, workspaces and approval."""
        return await _invite_people(
            client=backend_client,
            workspace_id=workspace_id,
            emails=emails,
            role=role,
            all_workspaces=all_workspaces,
            workspace_ids=workspace_ids,
            can_approve=can_approve,
        )

    @mcp_server.tool(annotations=DECIDES)
    async def update_person(
        workspace_id: WorkspaceId,
        person_id: Annotated[str, Field(description="The person's `id` from `list_people`.")],
        role: Annotated[Literal["admin", "member"] | None, Field(description="Their new role; leave out to keep it.")] = None,
        all_workspaces: Annotated[bool | None, Field(description="True for every workspace of the agency; false with `workspace_ids` for chosen ones; leave out to keep it.")] = None,
        workspace_ids: Annotated[list[str] | None, Field(description="The only workspaces they should reach; replaces their earlier choice.")] = None,
        can_approve: Annotated[bool | None, Field(description="Whether they may make the critical decisions; leave out to keep it.")] = None,
    ) -> UpdatePersonResult:
        """Change a person's role, the workspaces they reach, or whether they can
        approve. It applies at once, also to their assistants. Only for an admin's
        assistant, and only after the person said yes to this exact change. The last
        admin cannot be made a member."""
        return await _update_person(
            client=backend_client,
            workspace_id=workspace_id,
            person_id=person_id,
            role=role,
            all_workspaces=all_workspaces,
            workspace_ids=workspace_ids,
            can_approve=can_approve,
        )

    @mcp_server.tool(annotations=REMOVES)
    async def remove_person(
        workspace_id: WorkspaceId,
        person_id: Annotated[str, Field(description="A person's `id` or an invite's `id`, from `list_people`.")],
    ) -> RemovePersonResult:
        """Remove a person from the agency, or cancel an invite. A removed person and
        their assistants lose the agency's workspaces at once; what they did stays on
        record. Only for an admin's assistant, and only after the person said yes,
        having been told how many workspaces and assistants are affected."""
        return await _remove_person(
            client=backend_client, workspace_id=workspace_id, person_id=person_id
        )

    @mcp_server.tool(annotations=CONNECTS)
    async def connect_voice_platform(
        workspace_id: WorkspaceId,
        api_key: Annotated[str, Field(description="The platform's API key from the person; stored encrypted, never shown again.")],
        platform: Annotated[Literal["retell", "vapi", "elevenlabs"], Field(description="The voice platform. Retell for now.")] = "retell",
    ) -> ConnectVoicePlatformResult:
        """Connect the workspace's voice platform (Retell first) so Connexity can read
        its agents and calls. Ask the person for the API key, name the workspace, and
        never repeat the key. Connecting again replaces the earlier key."""
        return await _connect_voice_platform(
            client=backend_client,
            workspace_id=workspace_id,
            platform=platform,
            api_key=api_key,
        )

    @mcp_server.tool(annotations=CREATES)
    async def add_agents(
        workspace_id: WorkspaceId,
        agents: Annotated[list[AgentToAdd], Field(description="The Retell agents to add, up to 100.")],
    ) -> AddAgentsResult:
        """Add this client's agents to the workspace, linked to their Retell agents, so
        Connexity syncs their calls. Use your own Retell access to see the agents and
        their recent calls, ask the person which belong to this client, then pass their
        Retell agent ids (up to 100). Adding one already there changes nothing."""
        return await _add_agents(
            client=backend_client, workspace_id=workspace_id, agents=agents
        )

    @mcp_server.tool(annotations=SCANS)
    async def scan_calls(workspace_id: WorkspaceId) -> ScanCallsResult:
        """The first scan: bring the added agents' calls from the last 30 days into
        Connexity. Each call does one step of up to about a minute and says how far it
        has got; keep calling it until it says finished. Safe to repeat: it carries on
        where it stopped and skips calls already stored."""
        return await _scan_calls(client=backend_client, workspace_id=workspace_id)

    @mcp_server.tool(annotations=READ_ONLY)
    async def get_call(
        workspace_id: WorkspaceId,
        call_id: Annotated[str, Field(description="The call, from `list_calls`.")],
    ) -> GetCallResult:
        """One call in full: its timeline in order (agent and caller turns, and tool
        calls with arguments and result, secrets masked) and what the checks found,
        worst first, each pointing at its entry and saying whether a rule or a model
        found it. Find the call_id with list_calls."""
        return await _get_call(
            client=backend_client, workspace_id=workspace_id, call_id=call_id
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def list_calls(
        workspace_id: WorkspaceId,
        query: Annotated[str | None, Field(description="The end of a caller's number, or a whole call id.")] = None,
        agent_id: Annotated[str | None, Field(description="Only this agent's calls.")] = None,
        result: Annotated[str | None, Field(description="failed, degraded, clean or unchecked.")] = None,
        category: Annotated[str | None, Field(description="A category key, from `list_categories`.")] = None,
        period: Period = None,
        issue_id: Annotated[str | None, Field(description="Only the calls this issue was found on, with its findings.")] = None,
        version: Annotated[str | None, Field(description="Only calls on this agent version, from `get_agent`'s versions.")] = None,
        cursor: Cursor = None,
        limit: Limit = None,
    ) -> ListCallsResult:
        """The workspace's calls, newest first, with counts for the period. query is a
        phone number (matches the end of the caller's number) or a call id. Filters:
        agent_id, result (failed, degraded, clean, unchecked), category (a category
        key), period (7d, 30d, 90d), issue_id (only the calls that issue was found on,
        each with its moment and that issue's findings on it: events and detail),
        version (only calls on that agent version). Each call carries its agent version.
        limit (1 to 100) caps a page. Callers come as their last four digits."""
        return await _list_calls(
            client=backend_client,
            workspace_id=workspace_id,
            query=query,
            agent_id=agent_id,
            result=result,
            category=category,
            period=period,
            issue_id=issue_id,
            version=version,
            cursor=cursor,
            limit=limit,
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def read_calls(
        workspace_id: WorkspaceId,
        query: Annotated[str | None, Field(description="The end of a caller's number, or a whole call id.")] = None,
        agent_id: Annotated[str | None, Field(description="Only this agent's calls.")] = None,
        result: Annotated[str | None, Field(description="failed, degraded, clean or unchecked.")] = None,
        category: Annotated[str | None, Field(description="A category key, from `list_categories`.")] = None,
        period: Period = None,
        issue_id: Annotated[str | None, Field(description="Only the calls this issue was found on.")] = None,
        version: Annotated[str | None, Field(description="Only calls on this agent version, from `get_agent`'s versions.")] = None,
        cursor: Cursor = None,
        limit: Annotated[int | None, Field(description="The most calls in one answer, 1 to 50. A page may hold fewer: it also stops at a size limit.")] = None,
    ) -> ReadCallsResult:
        """Many calls in full in one answer, newest first: each call's conversation in
        order (what the agent and the caller said, and every tool call with its
        arguments and result), its result, agent version and what the checks found.
        Takes exactly `list_calls`' filters. Use it to measure a pattern across a
        period's calls yourself, such as how often a tool was called with an empty
        argument, instead of one `get_call` per call. A page holds as many calls as
        fit in one answer, usually 10 to 15: keep calling with `next_cursor` until
        there is none. Use `list_calls` when you only need the list, and `get_call`
        for one call's timings and the events its findings point at."""
        return await _read_calls(
            client=backend_client,
            workspace_id=workspace_id,
            query=query,
            agent_id=agent_id,
            result=result,
            category=category,
            period=period,
            issue_id=issue_id,
            version=version,
            cursor=cursor,
            limit=limit,
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def list_issues(
        workspace_id: WorkspaceId,
        query: Annotated[str | None, Field(description="Words in the title, or a whole issue id.")] = None,
        agent_id: Annotated[str | None, Field(description="Only this agent's issues.")] = None,
        category: Annotated[str | None, Field(description="A category key, from `list_categories`.")] = None,
        severity: Annotated[str | None, Field(description="critical or warning.")] = None,
        status: Annotated[str | None, Field(description="open (the default, with reopened), reopened, resolved or archived.")] = None,
        period: Period = None,
        version: Annotated[str | None, Field(description="Only issues found on this agent version's calls, counting those calls.")] = None,
        cursor: Cursor = None,
        limit: Limit = None,
    ) -> ListIssuesResult:
        """The workspace's issues, worst first, with counts (tiles) for the period:
        what Connexity's checks found on real calls. Each has its severity (critical or
        warning), how it was found (found_by: code_based, deterministic code; classifier
        or judge, a model), its
        category, and its size as calls affected of the agent's calls in the period.
        query matches words in the title or a whole issue id. Filters: agent_id,
        category (a category key), severity (critical, warning), status (open, the
        default and including reopened; reopened, resolved, archived), period (7d,
        30d, 90d), version (only issues found on that agent version's calls)."""
        return await _list_issues(
            client=backend_client,
            workspace_id=workspace_id,
            query=query,
            agent_id=agent_id,
            category=category,
            severity=severity,
            status=status,
            period=period,
            version=version,
            cursor=cursor,
            limit=limit,
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def get_issue(
        workspace_id: WorkspaceId,
        issue_id: IssueId,
        since_version: Annotated[str | None, Field(description="An agent version: answer how many real calls ran it or a later one since it went live, and how many have this issue. Omit for the version the issue is fixed in.")] = None,
    ) -> IssueResult:
        """Everything Connexity has about one issue: the check behind it (what it
        looks for, how it decides, its version, and for a model check the model),
        what each key of its findings' detail means, its setting for the agent, its
        size over the last 30 days (calls affected of the agent's calls), first and
        last seen, all-time counts, affected calls per agent version and the version
        live now, whether it is fixed in a version, calls per day with version marks,
        the latest calls it hit, and its history of decisions. `since_version` says
        whether it stopped after a fix: the agent's real calls since that version went
        live (on it or a later one) and how many have this issue; for an issue marked
        fixed it is given for the fix's version without asking. For the calls it was
        found on, with its findings in each, use `list_calls` with the issue_id."""
        return await _get_issue(
            client=backend_client,
            workspace_id=workspace_id,
            issue_id=issue_id,
            since_version=since_version,
        )

    @mcp_server.tool(annotations=DECIDES)
    async def archive_issue(
        workspace_id: WorkspaceId,
        issue_id: IssueId,
        reason: Annotated[str, Field(description="Why nobody will fix it, in the person's words.")],
        duration: Annotated[Literal["until_spike", "forever"], Field(description="until_spike brings it back if it happens twice as often; forever never does.")] = "until_spike",
    ) -> IssueResult:
        """Archive an issue nobody will fix: it is then hidden on every call and counts
        for nothing. A person's decision: first tell them the issue, its size and the
        duration, and call this only after they say yes, with their words as the
        reason. until_spike brings it back if it starts happening twice as often."""
        return await _archive_issue(
            client=backend_client,
            workspace_id=workspace_id,
            issue_id=issue_id,
            reason=reason,
            duration=duration,
        )

    @mcp_server.tool(annotations=CREATES)
    async def mark_issue_fixed(
        workspace_id: WorkspaceId,
        issue_id: IssueId,
        version: Annotated[str, Field(description="The agent's version on its platform that carries the fix.")],
        note: Annotated[str | None, Field(description="What you changed, in a sentence.")] = None,
    ) -> IssueResult:
        """Mark an issue fixed in the agent's version that carries the fix (its number
        on the platform), after you changed the agent. It becomes Resolved and leaves
        the open lists; Connexity waits for that version to go live on real calls, and
        reopens the issue if it happens again on a call after that. Refused if the
        issue was already found on calls of that version. note: what you changed."""
        return await _mark_issue_fixed(
            client=backend_client,
            workspace_id=workspace_id,
            issue_id=issue_id,
            version=version,
            note=note,
        )

    @mcp_server.tool(annotations=DECIDES)
    async def unarchive_issue(
        workspace_id: WorkspaceId,
        issue_id: IssueId,
        reason: Annotated[str | None, Field(description="Why it comes back, in the person's words.")] = None,
    ) -> IssueResult:
        """Bring an archived issue back: all its calls count again. Ask the person
        first, as for archiving."""
        return await _unarchive_issue(
            client=backend_client,
            workspace_id=workspace_id,
            issue_id=issue_id,
            reason=reason,
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def get_agent(
        workspace_id: WorkspaceId,
        agent_id: AgentId,
        period: Period = None,
        version: Annotated[str | None, Field(description="Count only this agent version's calls; `versions` lists them.")] = None,
    ) -> AgentResult:
        """One agent at a glance for the period (7d, 30d by default, 90d): platform,
        type, live version and since when, model, the n8n workflows it used, calls,
        latency p50 and p95 over every reply, each day's p50 with version marks,
        its spec state, and its score: 0 to 100 over its checked calls, its change
        against the previous period, the issues that cost it the most points, each
        day's score with its checked calls, and its open and critical issues counts. It
        lists every agent version that has a call; `version` counts only that
        version's calls, so two versions compare by calling twice."""
        return await _get_agent(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            period=period,
            version=version,
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def get_spec(
        workspace_id: WorkspaceId,
        agent_id: AgentId,
        version: Annotated[int | None, Field(description="A spec version. Leave empty for the latest.")] = None,
        compare: Annotated[int | None, Field(description="An earlier spec version to mark each rule kept, added or dropped against.")] = None,
    ) -> SpecResult:
        """An agent's spec: what it is supposed to do, as plain rules grouped by the
        fixed categories, each with its source (the prompt's words it rests on, or who
        answered the clarification) and whether an open question replaces it
        (in_conflict). state says none, current, or needs_review (the agent moved to a
        new version). versions lists every version; compare marks each rule kept,
        added or dropped against an earlier one. Read the agent's prompt from the
        voice platform, not from Connexity. Read connexity://guides/spec first."""
        return await _get_spec(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            version=version,
            compare=compare,
        )

    @mcp_server.tool(annotations=CREATES)
    async def write_spec(
        workspace_id: WorkspaceId,
        agent_id: AgentId,
        rules: Annotated[list[SpecRuleToWrite], Field(description="The agent's whole spec, every rule the prompt settles.")],
    ) -> SpecResult:
        """Write the agent's whole spec for its current version, as a new version.
        Each rule: one plain sentence, a category key, the prompt's exact words it
        rests on, touches (money, safety, compliance) when it protects one, the key
        of a rule kept from the previous version, and critical when a failure of the
        rule must stop a release. Only what the prompt settles;
        behaviour the prompt does not settle is a question for the person
        (`raise_clarifications`). Rules from the person's answers are carried over by
        Connexity; never pass them. Follow connexity://guides/spec."""
        return await _write_spec(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            rules=rules,
        )

    @mcp_server.tool(annotations=CREATES)
    async def mark_critical_rules(
        workspace_id: WorkspaceId,
        agent_id: AgentId,
        critical: Annotated[list[str] | None, Field(description="Rule keys, from `get_spec`, to mark critical.")] = None,
        not_critical: Annotated[list[str] | None, Field(description="Rule keys, from `get_spec`, to clear the mark from.")] = None,
    ) -> SpecResult:
        """Mark rules of the agent's latest spec critical (a failure stops a release)
        or clear the mark (a failure is a Warning), by the keys `get_spec` answers,
        without rewriting the spec. Rules from the person's answers can be marked too.
        Makes a new spec version with the rules unchanged; makes none when nothing
        changes. Yours to decide: no need to ask the person. Follow
        connexity://guides/spec, "Critical rules"."""
        return await _mark_critical_rules(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            critical=critical or [],
            not_critical=not_critical or [],
        )

    @mcp_server.tool(annotations=CREATES)
    async def write_scenarios(
        workspace_id: WorkspaceId,
        agent_id: AgentId,
        scenarios: Annotated[list[ScenarioToWrite], Field(description="Up to 20 scenarios, all or nothing.")],
    ) -> WriteScenariosResult:
        """Write scenarios for the agent: each a stage for a simulated call, with no
        pass or fail of its own. Each: a name; the caller (who, goal, behaviour); what
        the caller knows, kept apart from the agent's variables; who speaks first and
        the first message; fake tool results with invented values; and the keys of the
        spec rules it expects to come up (one or more, from `get_spec`). Pass `id` to
        replace one, `id` with `archive` to archive one. Up to 20 per call, all or
        nothing. Yours to write: no approval needed. Follow
        connexity://guides/scenarios."""
        return await _write_scenarios(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            scenarios=scenarios,
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def list_scenarios(
        workspace_id: WorkspaceId,
        agent_id: AgentId,
        rule_key: Annotated[str | None, Field(description="Only scenarios that list this spec rule.")] = None,
        set: Annotated[str | None, Field(description="Only scenarios in the set of this name.")] = None,
        cursor: Cursor = None,
        limit: Limit = None,
    ) -> ListScenariosResult:
        """The agent's active scenarios, oldest first, each with its rules (critical,
        or gone from the latest spec) and its sets; the agent's named sets; counts of
        rules listed and critical rules no scenario lists; and the rules without a
        scenario, critical first. Filter by `rule_key` or by a set's name (`set`);
        pass `next_cursor` back as `cursor` for the next page."""
        return await _list_scenarios(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            rule_key=rule_key,
            set_name=set,
            cursor=cursor,
            limit=limit,
        )

    # The assistant's own sets; the gate always runs every scenario (Dmytro, 2026-11-18).
    @mcp_server.tool(annotations=CREATES)
    async def write_scenario_set(
        workspace_id: WorkspaceId,
        agent_id: AgentId,
        name: Annotated[str, Field(description="The set's name; a set of that name is replaced.")],
        scenario_ids: Annotated[list[str], Field(description="The scenarios in the set, in order; empty archives the set.")],
        description: Annotated[str | None, Field(description="What the set is for, in a sentence.")] = None,
    ) -> ScenarioSetResult:
        """Create a named set of the agent's scenarios, or replace the set of that
        name, in the order given; an empty `scenario_ids` archives it. Sets are for
        your own runs (such as a small smoke set over the critical rules); the gate
        always runs every scenario."""
        return await _write_scenario_set(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            name=name,
            scenario_ids=scenario_ids,
            description=description,
        )

    @mcp_server.tool(annotations=RUNS)
    async def run_scenarios(
        workspace_id: WorkspaceId,
        agent_id: AgentId,
        set: Annotated[str | None, Field(description="Run the set of this name.")] = None,
        scenario_ids: Annotated[list[str] | None, Field(description="Or run these scenarios.")] = None,
        all: Annotated[bool, Field(description="Or run every active scenario.")] = False,
        repeats: Annotated[int | None, Field(description="Times each scenario runs, 1 to 5. Leave empty for 3.")] = None,
        version: Annotated[int | None, Field(description="The agent's version on its platform. Leave empty for the latest.")] = None,
        session: Annotated[str | None, Field(description="A few words naming this session's work, the same as on `get_next_task`; shown with the run.")] = None,
    ) -> RunScenariosResult:
        """Run the agent's scenarios in text: a named `set`, a pick of
        `scenario_ids`, or `all` (give exactly one). A simulated caller talks to the
        agent's own engine with every tool faked, until the agent hangs up or transfers
        or has answered 40 times; each scenario repeats `repeats`
        times (1 to 5, default 3), at most 200 simulated calls. `version` is the
        agent's version on its platform (default: the latest). Only `all` is a full
        run that decides the version's verdict; a set or a pick is on demand. Starts in
        the background; read the results with `get_test_runs`."""
        return await _run_scenarios(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            set_name=set,
            scenario_ids=scenario_ids,
            all_scenarios=all,
            repeats=repeats,
            version=version,
            session=session,
        )

    @mcp_server.tool(annotations=CREATES)
    async def send_feedback(
        workspace_id: WorkspaceId,
        kind: Annotated[str, Field(description="bug, or feature_request for something Connexity cannot do.")],
        title: Annotated[str, Field(description="One line: what is wrong or missing.")],
        what_happened: Annotated[str | None, Field(description="For a bug: what you did, which tool with which inputs, what you expected and what came back.")] = None,
        wanted: Annotated[str | None, Field(description="For a feature request: what the work needed and could not do.")] = None,
        tool: Annotated[str | None, Field(description="The Connexity tool involved.")] = None,
        error: Annotated[str | None, Field(description="The answer's error text, as it came.")] = None,
        ids: Annotated[list[str] | None, Field(description="The call, issue, run, agent or task ids involved.")] = None,
        session: Annotated[str | None, Field(description="A few words naming this session's work, the same as on `get_next_task`.")] = None,
    ) -> SendFeedbackResult:
        """Report a problem in Connexity itself to the Connexity team, who read every
        report: a Connexity tool that fails (after one retry), answers that contradict
        each other, or something the work needs that Connexity cannot do. Report
        without asking the person, once per problem, then tell them in a sentence. Not
        for problems in the person's own agent (those are issues). Never put caller
        data (transcripts, phone numbers, names) or secrets in a report: describe and
        give ids. At most 20 reports a day per workspace."""
        return await _send_feedback(
            client=backend_client,
            workspace_id=workspace_id,
            kind=kind,
            title=title,
            what_happened=what_happened,
            wanted=wanted,
            tool=tool,
            error=error,
            ids=ids,
            session=session,
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def get_test_runs(
        workspace_id: WorkspaceId,
        agent_id: AgentId,
        run_id: Annotated[str | None, Field(description="One run, from `run_scenarios` or this tool's runs.")] = None,
        version: Annotated[str | None, Field(description="A tested version. Leave empty for the newest.")] = None,
        status_only: Annotated[bool | None, Field(description="With `run_id`: answer only the run's status and counts (queued, running, finished, stalled). Use it to poll a run in progress.")] = None,
        cursor: Cursor = None,
        limit: Limit = None,
    ) -> TestRunsResult:
        """Without `run_id`: a tested version's results (`version`, default the
        newest tested version, live or not, with the live version's state beside it): Verified, Failed, Partially tested or Not verified, read from its
        latest full run, with that run's rules, code checks and stopped calls, every run
        of the version with its totals and who ran it, and coverage as tests written;
        then the agent's runs, newest first. With
        `run_id`: the run's status, rule totals, findings, and a page of its
        simulated calls with each rule's verdict, reason and link (`url`). Every run
        says what limits its result: whether its version was edited since (`content`,
        read on the platform now), the spec it judged against and whether the agent
        version is newer than it (`spec_behind`), verdicts that rest on a default fake
        (`mark`, not counted), and tool arguments that break the tool's own schema
        (`schema_check`, reported only); and how much
        of its sample it lost, where a call's time went (`timing`) and whether it is
        `stalled`. With `run_id` and `status_only`: the status and counts alone, for
        polling a run in progress."""
        return await _get_test_runs(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            run_id=run_id,
            version=version,
            status_only=status_only,
            cursor=cursor,
            limit=limit,
        )

    @mcp_server.tool(annotations=CREATES)
    async def raise_clarifications(
        workspace_id: WorkspaceId,
        agent_id: AgentId,
        questions: Annotated[list[QuestionToRaise], Field(description="Up to 20 questions for the person.")],
    ) -> RaiseClarificationsResult:
        """Raise questions for the person about behaviour the agent's spec does not
        settle, never deciding it yourself. Each question: one plain sentence with how
        often it happened, two to four answers each with the spec rule it becomes, a
        category key, touches when it protects money, safety or compliance, the calls
        where it was seen (none for a prompt change), and replaces_key to replace an
        answered rule a new prompt contradicts. Up to 20 per call; check
        `list_clarifications` first. Follow connexity://guides/spec."""
        return await _raise_clarifications(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            questions=questions,
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def list_clarifications(
        workspace_id: WorkspaceId,
        agent_id: Annotated[str | None, Field(description="Only this agent's questions.")] = None,
        state: Annotated[Literal["open", "answered", "parked"] | None, Field(description="open (the default), answered or parked.")] = None,
        cursor: Cursor = None,
        limit: Limit = None,
    ) -> ListClarificationsResult:
        """Questions for the person about the workspace's agents: open by default,
        most important first (seen on more calls, then money, safety or compliance,
        then newest), or answered or parked, newest first. Each has its answers (a to d) with the rule
        each becomes, how many calls it was seen on, and, once answered, the choice,
        who made it and the spec version it made. Counts of every state come with each
        page; pass `next_cursor` as `cursor` for the next."""
        return await _list_clarifications(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            state=state,
            cursor=cursor,
            limit=limit,
        )

    @mcp_server.tool(annotations=DECIDES)
    async def answer_clarifications(
        workspace_id: WorkspaceId,
        answers: Annotated[list[AnswerToGive], Field(description="The person's answers, parks and reopens.")],
    ) -> AnswerClarificationsResult:
        """Record the person's answers (a to d, or `other` with their own words as
        `text` when none of the choices fits), park questions (`park`), or bring a
        parked one back (`reopen`); each answer's rule is added to its agent's spec in
        a new version. The person's decision: ask them in your chat and confirm every
        answer first; answers you proposed and they confirmed are marked `proposed`.
        One left to you is still recorded as theirs. An answer is final."""
        return await _answer_clarifications(
            client=backend_client, workspace_id=workspace_id, answers=answers
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def list_categories(workspace_id: WorkspaceId) -> ListCategoriesResult:
        """The fixed categories every issue and spec rule belongs to, in their order:
        key, name and kind (behaviour or technical). The same set for every workspace;
        group issues and spec rules by it and use its names with the person."""
        return await _list_categories(client=backend_client, workspace_id=workspace_id)

    @mcp_server.tool(annotations=READ_ONLY)
    async def list_tasks(
        workspace_id: WorkspaceId, cursor: Cursor = None, limit: PageSize = 25
    ) -> ListTasksResult:
        """The workspace's whole task list, as the Work page shows it: in Connexity's
        order, each task in progress (with whose session), waiting for the person, or
        to do, with Blocks and Blocked by; what was done in the last 7 days; and the
        sessions working now. Read only: it never takes or ends a task (that is
        `get_next_task`). Pass `next_cursor` back as `cursor` for the next page (limit
        1 to 100)."""
        return await _list_tasks(
            client=backend_client, workspace_id=workspace_id, cursor=cursor, limit=limit
        )

    @mcp_server.tool(annotations=DECIDES)
    async def move_task(
        workspace_id: WorkspaceId,
        key: Annotated[str, Field(description="The task to move, from `list_tasks`: one in To do, or one you hold, which goes back to To do.")],
        before: Annotated[str | None, Field(description="The task it moves in front of. Leave empty for the end.")] = None,
    ) -> ListTasksResult:
        """Move a To do task (its `key` from `list_tasks`) to sit just before another
        (`before`; none for the end of the list): only when the person asks, such as
        "do Night line first"; never reorder on your own. Recorded as theirs with you as
        the assistant that acted. A task you hold goes back to To do, at its place or
        before `before`: do that when you stop working on it. Another assistant's
        tasks, questions waiting for the person, and incidents do not move. Answers the
        list in its new order."""
        return await _move_task(
            client=backend_client, workspace_id=workspace_id, key=key, before=before
        )

    # Takes the task for the caller and ends its previous one; asking again moves on.
    @mcp_server.tool(annotations=CREATES)
    async def get_next_task(
        workspace_id: WorkspaceId,
        session: Annotated[str | None, Field(description="A few words naming this session's work, the same on every call in it.")] = None,
    ) -> GetNextTaskResult:
        """Your next task in this workspace: the single most important thing to do,
        sorted by Connexity, with its facts, the rules and numbered steps naming the
        tools. Call it at the start of a session and after each task; asking again ends
        your current task (done, waiting for the person, or back in the list). Name
        this session in a few words for the work it is on (`session`, such as
        "Onboarding", up to 40 characters) and pass the same name on every call in it:
        each session holds its own task. Also lists what waits for the person, what
        other sessions are working on, and how many tasks are left."""
        return await _get_next_task(
            client=backend_client, workspace_id=workspace_id, session=session
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def get_dashboard(
        workspace_id: WorkspaceId,
        agent_id: Annotated[
            str | None, Field(description="One agent. Leave empty for all agents.")
        ] = None,
        period: Period = None,
    ) -> GetDashboardResult:
        """Where the workspace stands, the same picture as its Dashboard page, for all
        agents or one: calls, failed and degraded calls with their share, latency p50
        and p95 over every reply gap, the score with its change, calls per day with
        version marks, every area (category) as critical, warning, healthy or not
        checked yet with its top issue, and the onboarding strip while onboarding
        runs."""
        return await _get_dashboard(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            period=period,
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def get_usage(
        workspace_id: WorkspaceId,
        agent_id: Annotated[
            str | None, Field(description="One agent. Leave empty for all agents.")
        ] = None,
        period: Annotated[
            str | None,
            Field(
                description="month (a calendar month, UTC), 7d or 30d. Leave empty "
                "for month."
            ),
        ] = None,
        month: Annotated[
            str | None,
            Field(
                description="With period month: which one, as YYYY-MM. Leave empty "
                "for this month."
            ),
        ] = None,
        cursor: Cursor = None,
        limit: Limit = None,
        agency: Annotated[
            bool | None,
            Field(
                description="True to also get the whole agency's usage per workspace "
                "and agent (`agency_usage`), for billing each client. Only when the "
                "person you act for is an admin."
            ),
        ] = None,
        agency_period: Annotated[
            str | None,
            Field(
                description="With agency: this (the subscription's current period), "
                "last (the one before) or 30d. Leave empty for this, or 30d when "
                "there is no subscription."
            ),
        ] = None,
    ) -> GetUsageResult:
        """What the workspace used in a period and what that comes to at Connexity's
        list price; nothing is billed. Two meters: observed minutes (each real call,
        every started minute whole) and simulated caller messages (each message the
        simulated caller sent in a test run). Totals per meter in units and dollars,
        the same per agent, each run with its caller messages and cost (paged), and
        the three things that added most. Where paying is set up it also answers the
        agency's subscription (its state and when it renews or ends) and `money`:
        what is left of the period's included $299 and of the prepaid balance, and
        whether Connexity is paused for the agency. While it is paused, `add_agents`,
        `scan_calls` and `run_scenarios` are refused. You never start, pay, cancel or
        change a subscription, and never add funds. With `agency` an admin's assistant
        also gets the whole agency's usage per workspace and agent, counted by the
        subscription's period, to bill each client, with the latest invoices and the
        auto top-up setting, which you only read. Use it when the person asks what
        the work costs, what to bill a client, about their subscription, or before a
        large run."""
        return await _get_usage(
            client=backend_client,
            workspace_id=workspace_id,
            agent_id=agent_id,
            period=period,
            month=month,
            cursor=cursor,
            limit=limit,
            agency=agency,
            agency_period=agency_period,
        )

    @mcp_server.tool(annotations=READ_ONLY)
    async def get_readiness(workspace_id: WorkspaceId) -> GetReadinessResult:
        """How complete the workspace's setup is: each Getting started step, whether it
        is done, and what to do next. Call it after each setup step."""
        return await _get_readiness(client=backend_client, workspace_id=workspace_id)

    @mcp_server.tool(annotations=READ_ONLY)
    async def list_agents(
        workspace_id: WorkspaceId,
        query: Annotated[str | None, Field(description="Part of the agent's name.")] = None,
        period: Period = None,
        cursor: Cursor = None,
        limit: PageSize = 25,
    ) -> ListAgentsResult:
        """The agents in a workspace, newest first, each with its type
        (single_prompt or conversational_flow), its calls in the period (7d, 30d by
        default, 90d), its latency (p50 and p95 over every reply), its live version
        and since when, its spec state, its score with its change and its critical
        issues. `query`
        matches part of the name. Pass `next_cursor` back as `cursor` for the next page (limit 1 to
        100)."""
        return await _list_agents(
            client=backend_client,
            workspace_id=workspace_id,
            query=query,
            period=period,
            cursor=cursor,
            limit=limit,
        )

    for guide_name, guide_title in GUIDES.items():
        _register_guide(mcp_server, name=guide_name, title=guide_title)

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI):
        async with mcp_server.session_manager.run():
            try:
                yield
            finally:
                await token_verifier.aclose()
                await backend_client.aclose()

    app = FastAPI(title="Connexity MCP Server", lifespan=lifespan)
    app.state.mcp_server = mcp_server
    app.router.redirect_slashes = False

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    # Public and read only: the MCP contract the /mcp-docs page is built from. No
    # workspace data and no auth; it lists what any signed-in client would see.
    @app.get("/manifest", response_model=Manifest)
    async def manifest() -> Manifest:
        public = settings.resolved_mcp_public_base_url
        return await build_manifest(
            mcp_server,
            server_url=f"{public}{settings.normalized_mcp_path}" if public else None,
        )

    async def proxy_oauth_request(
        request: Request,
        backend_path: str,
    ) -> Response:
        cors_headers = _oauth_cors_headers(request=request, settings=settings)
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=cors_headers)

        upstream_url = f"{settings.normalized_backend_origin}{backend_path}"
        if request.url.query:
            upstream_url = f"{upstream_url}?{request.url.query}"

        body = await request.body()
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in {"host", "content-length"}
        }
        async with httpx.AsyncClient(
            timeout=settings.connexity_api_timeout_seconds,
            follow_redirects=False,
        ) as http_client:
            try:
                upstream_response = await http_client.request(
                    request.method,
                    upstream_url,
                    content=body,
                    headers=headers,
                )
            except httpx.HTTPError as exc:
                return JSONResponse(
                    {
                        "detail": (
                            "OAuth backend is not reachable from the MCP server. "
                            f"Expected backend origin: {settings.normalized_backend_origin}"
                        ),
                        "error": str(exc),
                    },
                    status_code=502,
                )

        response_headers = {
            key: value
            for key, value in upstream_response.headers.items()
            if key.lower()
            not in {
                "content-encoding",
                "content-length",
                "connection",
                "transfer-encoding",
            }
        }
        location = response_headers.get("location")
        if location:
            response_headers["location"] = _rewrite_backend_location(
                location=location,
                settings=settings,
            )
        response_headers.update(cors_headers)
        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=response_headers,
            media_type=upstream_response.headers.get("content-type"),
        )

    @app.api_route(
        "/.well-known/oauth-authorization-server",
        methods=["GET", "OPTIONS"],
    )
    async def oauth_authorization_server_metadata_proxy(request: Request) -> Response:
        return await proxy_oauth_request(
            request,
            "/.well-known/oauth-authorization-server",
        )

    @app.api_route(
        "/.well-known/openid-configuration",
        methods=["GET", "OPTIONS"],
    )
    async def openid_configuration_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/.well-known/openid-configuration")

    @app.api_route("/.well-known/jwks.json", methods=["GET", "OPTIONS"])
    async def jwks_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/.well-known/jwks.json")

    @app.api_route("/oauth/register", methods=["POST", "OPTIONS"])
    async def oauth_register_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/register")

    @app.api_route("/register", methods=["POST", "OPTIONS"])
    async def oauth_register_root_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/register")

    @app.api_route("/oauth/authorize", methods=["GET", "POST", "OPTIONS"])
    async def oauth_authorize_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize")

    @app.api_route("/authorize", methods=["GET", "POST", "OPTIONS"])
    async def oauth_authorize_root_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize")

    @app.api_route(
        "/oauth/authorize/confirm",
        methods=["POST", "OPTIONS"],
    )
    async def oauth_authorize_confirm_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize/confirm")

    @app.api_route("/oauth/authorize/allow", methods=["POST", "OPTIONS"])
    async def oauth_authorize_allow_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize/allow")

    @app.api_route("/oauth/authorize/cancel", methods=["POST", "OPTIONS"])
    async def oauth_authorize_cancel_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize/cancel")

    @app.api_route("/oauth/authorize/switch", methods=["GET", "OPTIONS"])
    async def oauth_authorize_switch_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize/switch")

    @app.api_route(
        "/oauth/authorize/signup",
        methods=["GET", "OPTIONS"],
    )
    async def oauth_authorize_signup_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize/signup")

    @app.api_route(
        "/oauth/authorize/signup/confirm",
        methods=["POST", "OPTIONS"],
    )
    async def oauth_authorize_signup_confirm_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/authorize/signup/confirm")

    @app.api_route("/token", methods=["POST", "OPTIONS"])
    async def oauth_token_root_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/token")

    @app.api_route("/oauth/token", methods=["POST", "OPTIONS"])
    async def oauth_token_proxy(request: Request) -> Response:
        return await proxy_oauth_request(request, "/oauth/token")

    protected_resource_metadata_url = build_resource_metadata_url(
        settings.validated_mcp_oauth_resource_server_url
    )
    protected_resource_metadata_path = urlparse(
        str(protected_resource_metadata_url)
    ).path
    protected_resource_metadata = {
        "resource": settings.resolved_mcp_oauth_resource_server_url,
        "authorization_servers": [settings.resolved_mcp_oauth_issuer_url],
        "scopes_supported": settings.resolved_mcp_oauth_required_scopes or None,
        "resource_name": settings.mcp_server_name,
    }
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": MCP_PROTOCOL_VERSION_HEADER,
    }

    @app.options(protected_resource_metadata_path)
    async def oauth_protected_resource_metadata_options() -> Response:
        return Response(status_code=204, headers=cors_headers)

    @app.get(protected_resource_metadata_path)
    async def oauth_protected_resource_metadata() -> JSONResponse:
        return JSONResponse(protected_resource_metadata, headers=cors_headers)

    if settings.normalized_mcp_path != "/":
        # Some hosted MCP clients probe the bare origin even when the
        # canonical transport is mounted at a subpath like `/mcp`.
        @app.options("/.well-known/oauth-protected-resource")
        async def oauth_protected_resource_metadata_root_options() -> Response:
            return Response(status_code=204, headers=cors_headers)

        @app.get("/.well-known/oauth-protected-resource")
        async def oauth_protected_resource_metadata_root() -> JSONResponse:
            return JSONResponse(protected_resource_metadata, headers=cors_headers)

    mcp_app = mcp_server.streamable_http_app()
    app.add_middleware(
        NormalizeMcpPathMiddleware, mcp_path=settings.normalized_mcp_path
    )
    app.mount(settings.normalized_mcp_path, mcp_app)
    app.mount(f"{settings.normalized_mcp_path}/", mcp_app)
    if settings.normalized_mcp_path != "/":
        app.mount("/", mcp_app)
    return app


def _register_guide(mcp_server: FastMCP, *, name: str, title: str) -> None:
    @mcp_server.resource(
        f"{GUIDE_URI_PREFIX}{name}",
        name=name,
        title=title,
        mime_type="text/markdown",
    )
    def guide() -> str:
        return read_guide(name)


def _rewrite_backend_location(*, location: str, settings: Settings) -> str:
    public_base_url = settings.resolved_mcp_public_base_url
    if not public_base_url:
        return location

    backend_origin = settings.normalized_backend_origin
    if location.startswith(backend_origin):
        return f"{public_base_url}{location[len(backend_origin):]}"
    return location


def _oauth_cors_headers(*, request: Request, settings: Settings) -> dict[str, str]:
    origin = request.headers.get("origin")
    if not origin or not _origin_is_allowed(
        origin=origin,
        allowed_origins=settings.resolved_allowed_origins,
    ):
        return {}

    requested_headers = request.headers.get("access-control-request-headers")
    allow_headers = requested_headers or "Authorization, Content-Type, Accept"
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": allow_headers,
        "Vary": "Origin",
    }


def _origin_is_allowed(*, origin: str, allowed_origins: list[str]) -> bool:
    origin_parts = urlparse(origin)
    for allowed_origin in allowed_origins:
        if origin == allowed_origin:
            return True

        if not allowed_origin.endswith(":*"):
            continue

        allowed_base = allowed_origin[:-2]
        allowed_parts = urlparse(allowed_base)
        if (
            allowed_parts.scheme == origin_parts.scheme
            and allowed_parts.hostname == origin_parts.hostname
            and origin_parts.port is not None
        ):
            return True

    return False
