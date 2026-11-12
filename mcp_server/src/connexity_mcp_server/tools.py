from __future__ import annotations

from connexity_mcp_server.client import ConnexityBackendClient
from connexity_mcp_server.models import (
    CreateWorkspaceResult,
    GetReadinessResult,
    ListAgentsResult,
    ListWorkspacesResult,
)


async def list_workspaces(client: ConnexityBackendClient) -> ListWorkspacesResult:
    return ListWorkspacesResult.model_validate(await client.list_workspaces())


async def create_workspace(
    client: ConnexityBackendClient, name: str
) -> CreateWorkspaceResult:
    return CreateWorkspaceResult.model_validate(
        await client.create_workspace(name=name)
    )


async def get_readiness(
    client: ConnexityBackendClient, workspace_id: str
) -> GetReadinessResult:
    return GetReadinessResult.model_validate(
        await client.get_readiness(workspace_id=workspace_id)
    )


async def list_agents(
    client: ConnexityBackendClient,
    workspace_id: str,
    query: str | None = None,
    cursor: str | None = None,
    limit: int = 25,
) -> ListAgentsResult:
    payload = await client.list_agents(
        workspace_id=workspace_id,
        query=query,
        cursor=cursor,
        limit=max(1, min(limit, 100)),
    )
    return ListAgentsResult.model_validate(payload)
