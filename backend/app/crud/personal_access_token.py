import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from app.crud.ingest_token import hash_ingest_token as hash_token
from app.models.personal_access_token import (
    PERSONAL_ACCESS_TOKEN_PREFIX,
    PERSONAL_ACCESS_TOKEN_VISIBLE_CHARS,
    PersonalAccessToken,
)
from app.models.workspace_member import WorkspaceMember

# "Last used" is written at most this often, so a busy assistant does not write a row
# on every call.
LAST_USED_RESOLUTION = timedelta(minutes=1)


def create_personal_access_token(
    *, session: Session, user_id: uuid.UUID, name: str
) -> tuple[PersonalAccessToken, str]:
    """Create a token for the person and return it with its secret.

    The person's earlier tokens that were never used are revoked, so copying the setup
    prompt twice does not leave a stray working token behind.
    """
    now = datetime.now(UTC)
    unused = session.exec(
        select(PersonalAccessToken).where(
            PersonalAccessToken.user_id == user_id,
            col(PersonalAccessToken.revoked_at).is_(None),
            col(PersonalAccessToken.last_used_at).is_(None),
        )
    ).all()
    for row in unused:
        row.revoked_at = now
        session.add(row)

    token = f"{PERSONAL_ACCESS_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
    created = PersonalAccessToken(
        user_id=user_id,
        name=name,
        prefix=token[:PERSONAL_ACCESS_TOKEN_VISIBLE_CHARS],
        token_hash=hash_token(token),
    )
    session.add(created)
    session.commit()
    session.refresh(created)
    return created, token


def list_personal_access_tokens(
    *, session: Session, user_id: uuid.UUID
) -> list[PersonalAccessToken]:
    """The person's tokens that still work, newest first."""
    return list(
        session.exec(
            select(PersonalAccessToken)
            .where(
                PersonalAccessToken.user_id == user_id,
                col(PersonalAccessToken.revoked_at).is_(None),
            )
            .order_by(col(PersonalAccessToken.created_at).desc())
        ).all()
    )


def get_personal_access_token(
    *, session: Session, token_id: uuid.UUID, user_id: uuid.UUID
) -> PersonalAccessToken | None:
    """The person's own token that still works; anyone else's is not found."""
    row = session.get(PersonalAccessToken, token_id)
    if row is None or row.user_id != user_id or row.revoked_at is not None:
        return None
    return row


def revoke_personal_access_token(
    *, session: Session, token: PersonalAccessToken
) -> PersonalAccessToken:
    if token.revoked_at is None:
        token.revoked_at = datetime.now(UTC)
        session.add(token)
        session.commit()
        session.refresh(token)
    return token


def use_personal_access_token(
    *, session: Session, token: str
) -> PersonalAccessToken | None:
    """The token's row if it still works, recording that it was used."""
    if not token.startswith(PERSONAL_ACCESS_TOKEN_PREFIX):
        return None
    row = session.exec(
        select(PersonalAccessToken).where(
            PersonalAccessToken.token_hash == hash_token(token)
        )
    ).first()
    if row is None or row.revoked_at is not None:
        return None
    now = datetime.now(UTC)
    last = row.last_used_at
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    if last is None or now - last >= LAST_USED_RESOLUTION:
        row.last_used_at = now
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def assistants_by_token(
    *, session: Session, company_id: uuid.UUID
) -> list[tuple[datetime, str]]:
    """Tokens of the workspace's members that an assistant has used and still work.

    Each as (first seen, name); a token counts as connected from its first use until
    it is revoked.
    """
    members = select(WorkspaceMember.user_id).where(
        WorkspaceMember.company_id == company_id
    )
    rows = session.exec(
        select(PersonalAccessToken).where(
            col(PersonalAccessToken.user_id).in_(members),
            col(PersonalAccessToken.revoked_at).is_(None),
            col(PersonalAccessToken.last_used_at).is_not(None),
        )
    ).all()
    found: list[tuple[datetime, str]] = []
    for row in rows:
        created = row.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        found.append((created, row.name))
    return found
