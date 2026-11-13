"""Backend routes behind the MCP server's tools.

Every route answers in the standard shape (`McpAnswer`): the facts, the rules that
apply, numbered next steps and a guide. Every route except `/mcp/workspaces` is scoped
to a workspace in its path, resolved by `require_mcp_workspace`.
"""

import base64
import binascii
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import col, select

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
from app.models import (
    Agent,
    CategoryPublic,
    IntegrationProvider,
    Platform,
    ReadinessPublic,
    ReadinessStepKey,
    ReadinessStepState,
    WorkspaceCreate,
)
from app.models.enums import CheckKind
from app.models.mcp import (
    GUIDE_CATEGORIES,
    GUIDE_CONNECT,
    GUIDE_GETTING_STARTED,
    GUIDE_ISSUES,
    GUIDE_READINESS,
    GUIDE_WORKSPACES,
    McpAddAgents,
    McpAddedAgents,
    McpAgent,
    McpAnswer,
    McpConnection,
    McpConnectVoicePlatform,
    McpErrorDetail,
    McpIssue,
    McpRefusedAgent,
    McpScanProgress,
    McpWorkspace,
)
from app.services.checks.registry import get_check
from app.services.connections import (
    KEY_LOCATION,
    VOICE_PLATFORMS,
    voice_platform_key_status,
    webhook_address,
)
from app.services.first_scan import SCAN_DAYS, scan_agents, scan_step
from app.services.retell import (
    dedupe_retell_agents,
    list_retell_agents,
    retell_key_status,
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
    "/workspaces/{workspace_id}/issues",
    response_model=McpAnswer[list[McpIssue]],
)
def list_issues(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    agent_id: uuid.UUID | None = Query(default=None),
    cursor: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
) -> McpAnswer[list[McpIssue]]:
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
    summaries = crud.list_workspace_issues(
        session=session, company_id=workspace.id, agent_id=agent_id
    )
    page = summaries[offset : offset + limit]
    has_more = offset + limit < len(summaries)
    agent_ids = list({s.issue.agent_id for s in page})
    names = {
        agent.id: agent.name
        for agent in session.exec(
            select(Agent).where(col(Agent.id).in_(agent_ids))
        ).all()
    }
    totals = crud.stored_call_counts(session=session, agent_ids=agent_ids)
    categories = crud.categories_by_id(session=session)
    data = []
    for summary in page:
        issue = summary.issue
        check = get_check(issue.check_type)
        kind = check.kind if check else summary.kind
        data.append(
            McpIssue(
                id=issue.id,
                agent_id=issue.agent_id,
                agent_name=names.get(issue.agent_id, ""),
                type=issue.check_type,
                title=check.title if check else issue.check_type,
                category=categories[issue.category_id].name,
                severity="critical" if summary.critical else "warning",
                found_by="rule" if kind in (None, CheckKind.RULE) else "model",
                state=issue.state.value,
                calls_affected=summary.call_count,
                calls_total=totals.get(issue.agent_id, 0),
                first_seen_at=summary.first_seen_at,
                last_seen_at=summary.last_seen_at,
            )
        )
    next_steps = []
    if has_more:
        next_steps.append(
            "Call `list_issues` again with `cursor` set to `next_cursor` for the next "
            "page."
        )
    if not summaries:
        next_steps.append(
            "No issues yet. Calls are checked within a minute of arriving; if the "
            "workspace has no calls, call `get_readiness`."
        )
    return McpAnswer[list[McpIssue]](
        data=data,
        rules=[
            "Worst first: open issues, then critical, then by calls affected.",
            "Say how each issue was found: found_by rule means deterministic code over "
            "the call; model means a classifier or judge.",
            "Give the size as 'in N of M calls' (calls_affected of calls_total), and "
            "group by category when you list several.",
            "Never quote what a caller said or a tool's arguments back to the person "
            "unless they ask for one call.",
        ],
        next_steps=next_steps,
        guide=GUIDE_ISSUES,
        next_cursor=_encode_cursor(offset + limit) if has_more else None,
    )


@router.get(
    "/workspaces/{workspace_id}/agents",
    response_model=McpAnswer[list[McpAgent]],
)
def list_agents(
    session: SessionDep,
    workspace: McpWorkspaceDep,
    query: str | None = Query(default=None, max_length=255),
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
    return McpAnswer[list[McpAgent]](
        data=[_mcp_agent(agent) for agent in agents],
        rules=[
            "Connexity never edits, deploys or calls an agent; it records and checks "
            "what the agent does.",
            "Agents are listed newest first; `query` matches part of the name, "
            "ignoring case.",
        ],
        next_steps=next_steps,
        guide=GUIDE_GETTING_STARTED,
        next_cursor=_encode_cursor(offset + limit) if has_more else None,
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
