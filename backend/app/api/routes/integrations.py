import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.core.encryption import decrypt
from app.models import (
    IntegrationCreate,
    IntegrationProvider,
    IntegrationPublic,
    IntegrationsPublic,
    Message,
)
from app.services.elevenlabs import check_elevenlabs_connection, list_elevenlabs_agents
from app.services.retell import (
    RetellAgentSummary,
    list_retell_agents,
    test_retell_connection,
)
from app.services.telnyx import (
    TelnyxAgentSummary,
    list_telnyx_agents,
    test_telnyx_connection,
)
from app.services.vapi import list_vapi_assistants, test_vapi_connection

_CONNECTION_TESTERS = {
    IntegrationProvider.RETELL: test_retell_connection,
    IntegrationProvider.TELNYX: test_telnyx_connection,
    IntegrationProvider.VAPI: test_vapi_connection,
    IntegrationProvider.ELEVENLABS: check_elevenlabs_connection,
}


async def _test_connection(provider: IntegrationProvider, api_key: str) -> bool:
    tester = _CONNECTION_TESTERS.get(provider)
    if tester is None:
        return False
    return await tester(api_key)


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
    integration_in: IntegrationCreate,
) -> IntegrationPublic:
    ok = await _test_connection(integration_in.provider, integration_in.api_key)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Could not connect to provider — check your API key and try again",
        )
    db_obj = crud.create_integration(session=session, data=integration_in)
    return IntegrationPublic.model_validate(db_obj)


@router.get("/", response_model=IntegrationsPublic)
def list_integrations(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> IntegrationsPublic:
    items, count = crud.list_integrations(session=session, skip=skip, limit=limit)
    return IntegrationsPublic(
        data=[IntegrationPublic.model_validate(i) for i in items],
        count=count,
    )


@router.delete("/{integration_id}", response_model=Message)
def delete_integration(
    session: SessionDep,
    integration_id: uuid.UUID,
) -> Message:
    integration = crud.get_integration(session=session, integration_id=integration_id)
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
    integration_id: uuid.UUID,
) -> Message:
    integration = crud.get_integration(session=session, integration_id=integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    api_key = decrypt(integration.encrypted_api_key)
    ok = await _test_connection(integration.provider, api_key)
    if not ok:
        raise HTTPException(status_code=400, detail="Connection test failed")
    return Message(message="Connection successful")


@router.get(
    "/{integration_id}/agents",
    response_model=list[RetellAgentSummary | TelnyxAgentSummary],
)
async def list_integration_agents(
    session: SessionDep,
    integration_id: uuid.UUID,
) -> list[RetellAgentSummary | TelnyxAgentSummary]:
    integration = crud.get_integration(session=session, integration_id=integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    api_key = decrypt(integration.encrypted_api_key)
    if integration.provider == IntegrationProvider.RETELL:
        agents = await list_retell_agents(api_key)
        return _dedupe_agents(agents)
    if integration.provider == IntegrationProvider.TELNYX:
        return await list_telnyx_agents(api_key)
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
