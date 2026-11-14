from __future__ import annotations

from connexity_mcp_server.client import ConnexityBackendClient
from connexity_mcp_server.models import (
    AddAgentsResult,
    AgentToAdd,
    ConnectVoicePlatformResult,
    CreateWorkspaceResult,
    GetCallResult,
    GetReadinessResult,
    ListAgentsResult,
    ListCallsResult,
    ListCategoriesResult,
    ListIssuesResult,
    ListWorkspacesResult,
    ScanCallsResult,
)


async def list_workspaces(client: ConnexityBackendClient) -> ListWorkspacesResult:
    return ListWorkspacesResult.model_validate(await client.list_workspaces())


async def create_workspace(
    client: ConnexityBackendClient, name: str
) -> CreateWorkspaceResult:
    return CreateWorkspaceResult.model_validate(
        await client.create_workspace(name=name)
    )


async def connect_voice_platform(
    client: ConnexityBackendClient, workspace_id: str, platform: str, api_key: str
) -> ConnectVoicePlatformResult:
    return ConnectVoicePlatformResult.model_validate(
        await client.connect_voice_platform(
            workspace_id=workspace_id, platform=platform, api_key=api_key
        )
    )


async def add_agents(
    client: ConnexityBackendClient, workspace_id: str, agents: list[AgentToAdd]
) -> AddAgentsResult:
    payload = [agent.model_dump(exclude_none=True) for agent in agents]
    return AddAgentsResult.model_validate(
        await client.add_agents(workspace_id=workspace_id, agents=payload)
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


async def scan_calls(client: ConnexityBackendClient, workspace_id: str) -> ScanCallsResult:
    return ScanCallsResult.model_validate(
        await client.scan_calls(workspace_id=workspace_id)
    )


async def list_categories(
    client: ConnexityBackendClient, workspace_id: str
) -> ListCategoriesResult:
    return ListCategoriesResult.model_validate(
        await client.list_categories(workspace_id=workspace_id)
    )


async def list_issues(
    client: ConnexityBackendClient,
    workspace_id: str,
    query: str | None = None,
    agent_id: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    period: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> ListIssuesResult:
    return ListIssuesResult.model_validate(
        await client.list_issues(
            workspace_id=workspace_id,
            query=query,
            agent_id=agent_id,
            category=category,
            severity=severity,
            status=status,
            period=period,
            cursor=cursor,
            limit=limit,
        )
    )


async def list_calls(
    client: ConnexityBackendClient,
    workspace_id: str,
    query: str | None = None,
    agent_id: str | None = None,
    result: str | None = None,
    category: str | None = None,
    period: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> ListCallsResult:
    return ListCallsResult.model_validate(
        await client.list_calls(
            workspace_id=workspace_id,
            query=query,
            agent_id=agent_id,
            result=result,
            category=category,
            period=period,
            cursor=cursor,
            limit=limit,
        )
    )


async def get_call(
    client: ConnexityBackendClient, workspace_id: str, call_id: str
) -> GetCallResult:
    return GetCallResult.model_validate(
        await client.get_call(workspace_id=workspace_id, call_id=call_id)
    )
