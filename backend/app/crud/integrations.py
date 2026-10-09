import uuid

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.encryption import encrypt, mask_key
from app.crud.call import soft_delete_calls_for_integration
from app.models.call import Call, CallEvent
from app.models.enums import CallEventType
from app.models.integration import (
    AgentToolBackend,
    Integration,
    IntegrationCreate,
)


def create_integration(
    *, session: Session, data: IntegrationCreate, company_id: uuid.UUID
) -> Integration:
    db_obj = Integration(
        company_id=company_id,
        provider=data.provider,
        name=data.name,
        base_url=data.base_url,
        encrypted_api_key=encrypt(data.api_key),
        masked_api_key=mask_key(data.api_key),
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_integration(
    *,
    session: Session,
    integration_id: uuid.UUID,
    company_id: uuid.UUID | None = None,
) -> Integration | None:
    statement = select(Integration).where(Integration.id == integration_id)
    if company_id is not None:
        statement = statement.where(Integration.company_id == company_id)
    return session.exec(statement).first()


def list_integrations(
    *,
    session: Session,
    company_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Integration], int]:
    count_statement = (
        select(func.count())
        .select_from(Integration)
        .where(Integration.company_id == company_id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(Integration)
        .where(Integration.company_id == company_id)
        .order_by(col(Integration.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    items = list(session.exec(statement).all())
    return items, count


def delete_integration(*, session: Session, db_integration: Integration) -> None:
    """Hard-delete the integration after detaching dependent rows.

    Calls are soft-deleted (rows kept so ``test_case.source_call_id`` FKs remain
    valid) and have their ``integration_id`` nulled. All in one transaction.
    """
    integration_id = db_integration.id
    soft_delete_calls_for_integration(session=session, integration_id=integration_id)
    session.delete(db_integration)
    session.commit()


def list_tool_backends(
    *, session: Session, agent_id: uuid.UUID
) -> list[tuple[AgentToolBackend, Integration]]:
    """An agent's tool-to-workflow mappings, each with its connection."""
    statement = (
        select(AgentToolBackend, Integration)
        .join(Integration, col(Integration.id) == col(AgentToolBackend.integration_id))
        .where(AgentToolBackend.agent_id == agent_id)
        .order_by(col(AgentToolBackend.tool_name))
    )
    return [(row[0], row[1]) for row in session.exec(statement).all()]


def set_tool_backend(
    *,
    session: Session,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    tool_name: str,
    integration_id: uuid.UUID,
    workflow_id: str,
    workflow_name: str,
) -> AgentToolBackend:
    """Map a tool to a workflow, replacing any mapping the tool already has."""
    backend = session.get(AgentToolBackend, (agent_id, tool_name))
    if backend is None:
        backend = AgentToolBackend(
            agent_id=agent_id,
            tool_name=tool_name,
            company_id=company_id,
            integration_id=integration_id,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
        )
    else:
        backend.integration_id = integration_id
        backend.workflow_id = workflow_id
        backend.workflow_name = workflow_name
    session.add(backend)
    session.commit()
    session.refresh(backend)
    return backend


def clear_tool_backend(
    *, session: Session, agent_id: uuid.UUID, tool_name: str
) -> bool:
    """Remove a tool's mapping. Returns whether it had one."""
    backend = session.get(AgentToolBackend, (agent_id, tool_name))
    if backend is None:
        return False
    session.delete(backend)
    session.commit()
    return True


def count_tool_calls_by_name(
    *, session: Session, agent_id: uuid.UUID
) -> dict[str, int]:
    """How often each tool name appears in the agent's stored calls."""
    statement = (
        select(CallEvent.name, func.count())
        .join(Call, col(Call.id) == col(CallEvent.call_id))
        .where(
            Call.agent_id == agent_id,
            col(Call.deleted_at).is_(None),
            CallEvent.type == CallEventType.TOOL_CALL,
            col(CallEvent.name).is_not(None),
        )
        .group_by(col(CallEvent.name))
    )
    return {str(name): int(count) for name, count in session.exec(statement)}
