"""The catalogue of component versions seen for an agent."""

import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import defer
from sqlmodel import Session, col, select

from app.models.component_version import ComponentVersion


def get_component_version(
    *, session: Session, agent_id: uuid.UUID, kind: str, ref: str, version: str
) -> ComponentVersion | None:
    return session.exec(
        select(ComponentVersion).where(
            ComponentVersion.agent_id == agent_id,
            ComponentVersion.kind == kind,
            ComponentVersion.ref == ref,
            ComponentVersion.version == version,
        )
    ).first()


def record_component_version(
    *,
    session: Session,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    kind: str,
    name: str,
    ref: str,
    version: str,
    fingerprint: str,
    content: Any,
    links: list[dict[str, str]] | None = None,
) -> tuple[ComponentVersion, bool]:
    """Record a version if it is not in the catalogue yet.

    A version already recorded is left as it is: the first observation stands. Safe to
    call concurrently for the same version.

    Returns:
        The catalogue entry, and whether this call created it.
    """
    table: Any = ComponentVersion.__table__  # type: ignore[attr-defined]
    inserted = session.execute(
        pg_insert(table)
        .values(
            id=uuid.uuid4(),
            company_id=company_id,
            agent_id=agent_id,
            kind=kind,
            name=name[:255],
            ref=ref,
            version=version,
            fingerprint=fingerprint,
            content=content,
            links=links,
        )
        .on_conflict_do_nothing(constraint="uq_component_version_identity")
        .returning(table.c.id)
    ).first()
    session.commit()
    row = get_component_version(
        session=session, agent_id=agent_id, kind=kind, ref=ref, version=version
    )
    if row is None:
        msg = "A component version vanished between insert and read"
        raise RuntimeError(msg)
    return row, inserted is not None


def list_component_versions(
    *, session: Session, agent_id: uuid.UUID, kind: str | None = None
) -> list[ComponentVersion]:
    """An agent's catalogue, without the content: that is read one entry at a time."""
    statement = (
        select(ComponentVersion)
        .where(ComponentVersion.agent_id == agent_id)
        .options(defer(ComponentVersion.content))  # type: ignore[arg-type]
    )
    if kind is not None:
        statement = statement.where(ComponentVersion.kind == kind)
    return list(
        session.exec(
            statement.order_by(
                col(ComponentVersion.kind), col(ComponentVersion.first_seen_at).desc()
            )
        ).all()
    )


def get_component_version_by_id(
    *, session: Session, component_version_id: uuid.UUID, agent_id: uuid.UUID
) -> ComponentVersion | None:
    row = session.get(ComponentVersion, component_version_id)
    return row if row is not None and row.agent_id == agent_id else None
