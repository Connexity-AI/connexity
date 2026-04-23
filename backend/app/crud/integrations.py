import uuid

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.encryption import encrypt, mask_key
from app.models.integration import Integration, IntegrationCreate


def create_integration(
    *, session: Session, data: IntegrationCreate, user_id: uuid.UUID
) -> Integration:
    db_obj = Integration(
        provider=data.provider,
        name=data.name,
        encrypted_api_key=encrypt(data.api_key),
        masked_api_key=mask_key(data.api_key),
        user_id=user_id,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_integration(
    *, session: Session, integration_id: uuid.UUID, user_id: uuid.UUID
) -> Integration | None:
    statement = select(Integration).where(
        Integration.id == integration_id,
        Integration.user_id == user_id,
    )
    return session.exec(statement).first()


def list_integrations(
    *,
    session: Session,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Integration], int]:
    count_statement = (
        select(func.count())
        .select_from(Integration)
        .where(Integration.user_id == user_id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(Integration)
        .where(Integration.user_id == user_id)
        .order_by(col(Integration.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    items = list(session.exec(statement).all())
    return items, count


def delete_integration(*, session: Session, db_integration: Integration) -> None:
    session.delete(db_integration)
    session.commit()
