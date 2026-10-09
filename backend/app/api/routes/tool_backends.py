"""Which workflow serves each of an agent's tools."""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.core.encryption import decrypt
from app.models import (
    AgentToolPublic,
    IntegrationProvider,
    Message,
    ToolBackendPublic,
    ToolBackendSet,
)
from app.services.executions import (
    find_missing_executions_in_background,
    forget_lookups_for_tool,
)
from app.services.n8n import N8nError, get_n8n_workflow

router = APIRouter(
    prefix="/agents/{agent_id}",
    tags=["tool-backends"],
    dependencies=[Depends(get_current_user)],
)


def _require_agent(
    session: SessionDep, company_id: uuid.UUID, agent_id: uuid.UUID
) -> None:
    if (
        crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
        is None
    ):
        raise HTTPException(status_code=404, detail="Agent not found")


@router.get("/tools", response_model=list[AgentToolPublic])
def list_agent_tools(
    session: SessionDep, company_id: CurrentCompany, agent_id: uuid.UUID
) -> list[AgentToolPublic]:
    """The tools seen in the agent's calls, each with the workflow it is mapped to.

    A mapped tool is listed even when no stored call has used it.
    """
    _require_agent(session, company_id, agent_id)
    counts = crud.count_tool_calls_by_name(session=session, agent_id=agent_id)
    backends = {
        backend.tool_name: ToolBackendPublic(
            integration_id=integration.id,
            integration_name=integration.name,
            workflow_id=backend.workflow_id,
            workflow_name=backend.workflow_name,
        )
        for backend, integration in crud.list_tool_backends(
            session=session, agent_id=agent_id
        )
    }
    return [
        AgentToolPublic(
            name=name, call_count=counts.get(name, 0), backend=backends.get(name)
        )
        for name in sorted(set(counts) | set(backends), key=str.lower)
    ]


@router.put("/tool-backends", response_model=ToolBackendPublic)
async def set_agent_tool_backend(
    session: SessionDep,
    background_tasks: BackgroundTasks,
    company_id: CurrentCompany,
    agent_id: uuid.UUID,
    body: ToolBackendSet,
) -> ToolBackendPublic:
    """Map a tool to a workflow in one of the company's n8n connections.

    The tool's recent calls are then looked up for their executions, after the response.
    """
    _require_agent(session, company_id, agent_id)
    integration = crud.get_integration(
        session=session, integration_id=body.integration_id, company_id=company_id
    )
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    if integration.provider != IntegrationProvider.N8N:
        raise HTTPException(
            status_code=400, detail="A tool can only be mapped to an n8n connection"
        )
    try:
        workflow = await get_n8n_workflow(
            integration.base_url or "",
            decrypt(integration.encrypted_api_key),
            body.workflow_id,
        )
    except N8nError as exc:
        raise HTTPException(status_code=502, detail=f"n8n: {exc}") from exc
    if workflow is None:
        raise HTTPException(
            status_code=404, detail="That n8n has no workflow with this id"
        )
    backend = crud.set_tool_backend(
        session=session,
        agent_id=agent_id,
        company_id=company_id,
        tool_name=body.tool_name,
        integration_id=integration.id,
        workflow_id=workflow.id,
        workflow_name=workflow.name[:255],
    )
    forget_lookups_for_tool(
        session=session, agent_id=agent_id, tool_name=body.tool_name
    )
    background_tasks.add_task(find_missing_executions_in_background, agent_id)
    return ToolBackendPublic(
        integration_id=integration.id,
        integration_name=integration.name,
        workflow_id=backend.workflow_id,
        workflow_name=backend.workflow_name,
    )


@router.delete("/tool-backends", response_model=Message)
def clear_agent_tool_backend(
    session: SessionDep,
    company_id: CurrentCompany,
    agent_id: uuid.UUID,
    tool_name: str = Query(min_length=1, max_length=255),
) -> Message:
    _require_agent(session, company_id, agent_id)
    if not crud.clear_tool_backend(
        session=session, agent_id=agent_id, tool_name=tool_name
    ):
        raise HTTPException(status_code=404, detail="This tool has no mapping")
    return Message(message="Mapping removed")
