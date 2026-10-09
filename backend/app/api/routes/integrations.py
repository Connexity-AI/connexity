import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.core.encryption import decrypt
from app.models import (
    IntegrationCreate,
    IntegrationProvider,
    IntegrationPublic,
    IntegrationsPublic,
    Message,
    WorkflowSummary,
)
from app.services.elevenlabs import check_elevenlabs_connection, list_elevenlabs_agents
from app.services.n8n import N8nError, check_n8n_connection, list_n8n_workflows
from app.services.outbound_url import OutboundUrlError, normalize_base_url
from app.services.retell import (
    RetellAgentSummary,
    list_retell_agents,
    test_retell_connection,
)
from app.services.vapi import list_vapi_assistants, test_vapi_connection

_CONNECTION_TESTERS = {
    IntegrationProvider.RETELL: test_retell_connection,
    IntegrationProvider.VAPI: test_vapi_connection,
    IntegrationProvider.ELEVENLABS: check_elevenlabs_connection,
}


# Providers whose connection is to the user's own instance, so it needs an address.
_PROVIDERS_WITH_ADDRESS = {IntegrationProvider.N8N}


async def _test_connection(
    provider: IntegrationProvider, api_key: str, base_url: str | None
) -> str | None:
    """Try the connection. Returns ``None`` when it works, else what went wrong."""
    if provider == IntegrationProvider.N8N:
        if not base_url:
            return "An n8n connection needs the address of the n8n instance"
        result = await check_n8n_connection(base_url, api_key)
        return None if result.ok else result.message
    tester = _CONNECTION_TESTERS.get(provider)
    if tester is None or not await tester(api_key):
        return "Could not connect to provider — check your API key and try again"
    return None


def _agent_priority(agent: RetellAgentSummary) -> tuple[int, int]:
    published_rank = 1 if agent.is_published else 0
    version_rank = agent.version if agent.version is not None else -1
    return (published_rank, version_rank)


def _dedupe_agents(agents: list[RetellAgentSummary]) -> list[RetellAgentSummary]:
    by_id: dict[str, RetellAgentSummary] = {}
    for agent in agents:
        existing = by_id.get(agent.agent_id)
        if existing is None:
            by_id[agent.agent_id] = agent
            continue
        if _agent_priority(agent) > _agent_priority(existing):
            by_id[agent.agent_id] = agent
    return list(by_id.values())


router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=IntegrationPublic)
async def create_integration(
    session: SessionDep,
    company_id: CurrentCompany,
    integration_in: IntegrationCreate,
) -> IntegrationPublic:
    if integration_in.provider in _PROVIDERS_WITH_ADDRESS:
        try:
            integration_in.base_url = normalize_base_url(integration_in.base_url or "")
        except OutboundUrlError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif not (integration_in.base_url or "").strip():
        integration_in.base_url = None
    else:
        raise HTTPException(
            status_code=400, detail="This provider does not take an address"
        )
    problem = await _test_connection(
        integration_in.provider, integration_in.api_key, integration_in.base_url
    )
    if problem is not None:
        raise HTTPException(status_code=400, detail=problem)
    db_obj = crud.create_integration(
        session=session, data=integration_in, company_id=company_id
    )
    return IntegrationPublic.model_validate(db_obj)


@router.get("/", response_model=IntegrationsPublic)
def list_integrations(
    session: SessionDep,
    company_id: CurrentCompany,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> IntegrationsPublic:
    items, count = crud.list_integrations(
        session=session, company_id=company_id, skip=skip, limit=limit
    )
    return IntegrationsPublic(
        data=[IntegrationPublic.model_validate(i) for i in items],
        count=count,
    )


@router.delete("/{integration_id}", response_model=Message)
def delete_integration(
    session: SessionDep,
    company_id: CurrentCompany,
    integration_id: uuid.UUID,
) -> Message:
    integration = crud.get_integration(
        session=session, integration_id=integration_id, company_id=company_id
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    env_count = crud.count_environments_for_integration(
        session=session, integration_id=integration_id
    )
    if env_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete integration: {env_count} environment(s) depend on it",
        )
    crud.delete_integration(session=session, db_integration=integration)
    return Message(message="Integration deleted successfully")


@router.post("/{integration_id}/test", response_model=Message)
async def test_integration(
    session: SessionDep,
    company_id: CurrentCompany,
    integration_id: uuid.UUID,
) -> Message:
    integration = crud.get_integration(
        session=session, integration_id=integration_id, company_id=company_id
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    api_key = decrypt(integration.encrypted_api_key)
    problem = await _test_connection(
        integration.provider, api_key, integration.base_url
    )
    if problem is not None:
        raise HTTPException(
            status_code=400, detail=f"Connection test failed: {problem}"
        )
    return Message(message="Connection successful")


@router.get("/{integration_id}/agents", response_model=list[RetellAgentSummary])
async def list_integration_agents(
    session: SessionDep,
    company_id: CurrentCompany,
    integration_id: uuid.UUID,
) -> list[RetellAgentSummary]:
    integration = crud.get_integration(
        session=session, integration_id=integration_id, company_id=company_id
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    api_key = decrypt(integration.encrypted_api_key)
    if integration.provider == IntegrationProvider.RETELL:
        agents = await list_retell_agents(api_key)
        return _dedupe_agents(agents)
    if integration.provider == IntegrationProvider.VAPI:
        assistants = await list_vapi_assistants(api_key)
        mapped = [
            RetellAgentSummary(
                agent_id=assistant.agent_id,
                agent_name=assistant.agent_name,
                is_published=assistant.is_published,
                version=assistant.version,
            )
            for assistant in assistants
        ]
        return _dedupe_agents(mapped)
    if integration.provider == IntegrationProvider.ELEVENLABS:
        agents = await list_elevenlabs_agents(api_key)
        mapped = [
            RetellAgentSummary(
                agent_id=agent.agent_id,
                agent_name=agent.agent_name,
                is_published=agent.is_published,
                version=agent.version,
            )
            for agent in agents
        ]
        return _dedupe_agents(mapped)
    raise HTTPException(status_code=400, detail="Provider does not expose agents")


@router.get("/{integration_id}/workflows", response_model=list[WorkflowSummary])
async def list_integration_workflows(
    session: SessionDep,
    company_id: CurrentCompany,
    integration_id: uuid.UUID,
) -> list[WorkflowSummary]:
    """The names of an n8n connection's workflows, for mapping a tool to one."""
    integration = crud.get_integration(
        session=session, integration_id=integration_id, company_id=company_id
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    if integration.provider != IntegrationProvider.N8N:
        raise HTTPException(status_code=400, detail="Provider has no workflows")
    try:
        workflows = await list_n8n_workflows(
            integration.base_url or "", decrypt(integration.encrypted_api_key)
        )
    except N8nError as exc:
        raise HTTPException(status_code=502, detail=f"n8n: {exc}") from exc
    return [
        WorkflowSummary(id=workflow.id, name=workflow.name, active=workflow.active)
        for workflow in workflows
    ]
