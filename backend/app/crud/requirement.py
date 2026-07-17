import uuid

from sqlalchemy import delete as sa_delete
from sqlmodel import Session, col, select

from app.models import AgentVersion, Requirement
from app.models.enums import RequirementsStatus
from app.services.requirement_extractor import RequirementDraft


def set_requirements_status(
    *,
    session: Session,
    agent_version_id: uuid.UUID,
    status: RequirementsStatus,
) -> None:
    version = session.get(AgentVersion, agent_version_id)
    if version is None:
        return
    version.requirements_status = status
    session.add(version)
    session.commit()


def replace_requirements_for_version(
    *,
    session: Session,
    agent_id: uuid.UUID,
    agent_version_id: uuid.UUID,
    company_id: uuid.UUID,
    drafts: list[RequirementDraft],
) -> list[Requirement]:
    """Replace the requirement snapshot for a version (immutable per version).

    Idempotent: re-extraction for the same version clears prior rows first.
    """
    session.execute(
        sa_delete(Requirement).where(
            col(Requirement.agent_version_id) == agent_version_id
        )
    )
    rows: list[Requirement] = []
    for index, draft in enumerate(drafts):
        row = Requirement(
            company_id=company_id,
            agent_id=agent_id,
            agent_version_id=agent_version_id,
            text=draft.text,
            category=draft.category,
            source_ref=draft.source_ref,
            order_index=index,
        )
        session.add(row)
        rows.append(row)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def list_requirements_for_version(
    *, session: Session, agent_version_id: uuid.UUID
) -> list[Requirement]:
    statement = (
        select(Requirement)
        .where(Requirement.agent_version_id == agent_version_id)
        .order_by(col(Requirement.order_index))
    )
    return list(session.exec(statement).all())


def has_requirements_for_version(
    *, session: Session, agent_version_id: uuid.UUID
) -> bool:
    statement = (
        select(Requirement.id)
        .where(Requirement.agent_version_id == agent_version_id)
        .limit(1)
    )
    return session.exec(statement).first() is not None
