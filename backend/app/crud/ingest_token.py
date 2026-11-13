import secrets
import uuid
from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.core.security import hash_api_token
from app.models.ingest_token import (
    INGEST_TOKEN_PREFIX,
    INGEST_TOKEN_VISIBLE_CHARS,
    IngestToken,
)


def hash_ingest_token(token: str) -> str:
    return hash_api_token(token)


def create_ingest_token(
    *,
    session: Session,
    company_id: uuid.UUID,
    name: str,
    created_by: uuid.UUID | None = None,
) -> tuple[IngestToken, str]:
    """Create a token and return it with its secret. The secret is not stored."""
    token = f"{INGEST_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
    row = IngestToken(
        company_id=company_id,
        name=name,
        prefix=token[:INGEST_TOKEN_VISIBLE_CHARS],
        token_hash=hash_ingest_token(token),
        created_by=created_by,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row, token


def list_ingest_tokens(*, session: Session, company_id: uuid.UUID) -> list[IngestToken]:
    return list(
        session.exec(
            select(IngestToken)
            .where(IngestToken.company_id == company_id)
            .order_by(col(IngestToken.created_at).desc())
        ).all()
    )


def get_ingest_token(
    *, session: Session, token_id: uuid.UUID, company_id: uuid.UUID
) -> IngestToken | None:
    row = session.get(IngestToken, token_id)
    if row is None or row.company_id != company_id:
        return None
    return row


def revoke_ingest_token(*, session: Session, token: IngestToken) -> IngestToken:
    if token.revoked_at is None:
        token.revoked_at = datetime.now(UTC).replace(tzinfo=None)
        session.add(token)
        session.commit()
        session.refresh(token)
    return token


def use_ingest_token(*, session: Session, token: str) -> IngestToken | None:
    """Return the live token row for ``token`` and record that it was used."""
    row = session.exec(
        select(IngestToken).where(IngestToken.token_hash == hash_ingest_token(token))
    ).first()
    if row is None or row.revoked_at is not None:
        return None
    row.last_used_at = datetime.now(UTC).replace(tzinfo=None)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
