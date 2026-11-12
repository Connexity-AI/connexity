"""Backend routes behind the MCP server's tools.

Every route answers in the standard shape (`McpAnswer`): the facts, the rules that
apply, numbered next steps and a guide. Every route except `/mcp/workspaces` is scoped
to a workspace in its path, resolved by `require_mcp_workspace`.
"""

import base64
import binascii

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
from app.models import (
    IntegrationProvider,
    ReadinessPublic,
    ReadinessStepKey,
    ReadinessStepState,
    WorkspaceCreate,
)
from app.models.mcp import (
    GUIDE_CONNECT,
    GUIDE_GETTING_STARTED,
    GUIDE_READINESS,
    GUIDE_WORKSPACES,
    McpAgent,
    McpAnswer,
    McpConnection,
    McpConnectVoicePlatform,
    McpErrorDetail,
    McpWorkspace,
)
from app.services.connections import (
    KEY_LOCATION,
    VOICE_PLATFORMS,
    voice_platform_key_status,
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
        data=[
            McpAgent(
                id=agent.id,
                name=agent.name,
                platform=agent.platform,
                platform_agent_name=agent.platform_agent_name,
                created_at=agent.created_at,
            )
            for agent in agents
        ],
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
    if state[ReadinessStepKey.SYNC] != ReadinessStepState.DONE:
        if state[ReadinessStepKey.VOICE_PLATFORM] == ReadinessStepState.DONE:
            next_steps.append(
                "The voice platform is connected. Choosing agents to sync and the "
                "first scan are not available in Connexity yet; tell the person so, "
                "and do not ask for the key again."
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
