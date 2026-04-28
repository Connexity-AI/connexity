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
from app.services.retell import (
    RetellAgentSummary,
    list_retell_agents,
    test_retell_connection,
)

_CONNECTION_TESTERS = {
    IntegrationProvider.RETELL: test_retell_connection,
}


async def _test_connection(provider: IntegrationProvider, api_key: str) -> bool:
    tester = _CONNECTION_TESTERS.get(provider)
    if tester is None:
        return False
    return await tester(api_key)


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


@router.get("/{integration_id}/agents", response_model=list[RetellAgentSummary])
async def list_integration_agents(
    session: SessionDep,
    integration_id: uuid.UUID,
) -> list[RetellAgentSummary]:
    integration = crud.get_integration(session=session, integration_id=integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    api_key = decrypt(integration.encrypted_api_key)
    return await list_retell_agents(api_key)
