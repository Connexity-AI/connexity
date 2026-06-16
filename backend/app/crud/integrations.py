import uuid

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.encryption import encrypt, mask_key
from app.crud.call import soft_delete_calls_for_integration
from app.models.integration import Integration, IntegrationCreate


def create_integration(
    *, session: Session, data: IntegrationCreate, company_id: uuid.UUID
) -> Integration:
    db_obj = Integration(
        company_id=company_id,
        provider=data.provider,
        name=data.name,
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
