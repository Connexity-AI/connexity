import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import Agent, Run
from app.models.prompt_editor import (
    PromptEditorMessage,
    PromptEditorSession,
    PromptEditorSessionCreate,
    PromptEditorSessionUpdate,
)


def create_session(
    *,
    session: Session,
    session_in: PromptEditorSessionCreate,
    created_by: uuid.UUID,
) -> PromptEditorSession:
    """Create a prompt editor session; validate agent and optional run ownership."""
    agent = session.get(Agent, session_in.agent_id)
    if agent is None:
        msg = "Agent not found"
        raise ValueError(msg)
    if session_in.run_id is not None:
        run = session.get(Run, session_in.run_id)
        if run is None:
            msg = "Run not found"
            raise ValueError(msg)
        if run.agent_id != session_in.agent_id:
            msg = "Run does not belong to agent"
            raise ValueError(msg)

    title = session_in.title
    if title is None or not str(title).strip():
        title = f"Session {datetime.now(UTC).date().isoformat()}"

    db_obj = PromptEditorSession(
        agent_id=session_in.agent_id,
        created_by=created_by,
        run_id=session_in.run_id,
        title=title,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_session(
    *, session: Session, session_id: uuid.UUID
) -> PromptEditorSession | None:
    return session.get(PromptEditorSession, session_id)


def list_sessions(
    *,
    session: Session,
    agent_id: uuid.UUID | None,
    created_by: uuid.UUID | None,
    skip: int,
    limit: int,
) -> tuple[list[tuple[PromptEditorSession, int]], int]:
    """List sessions with optional filters; each tuple contains (session, message_count)."""
    count_stmt = select(func.count()).select_from(PromptEditorSession)
    if agent_id is not None:
        count_stmt = count_stmt.where(col(PromptEditorSession.agent_id) == agent_id)
    if created_by is not None:
        count_stmt = count_stmt.where(col(PromptEditorSession.created_by) == created_by)
    total = session.exec(count_stmt).one()

    msg_counts = (
        select(
            col(PromptEditorMessage.session_id),
            func.count(col(PromptEditorMessage.id)).label("cnt"),
        )
        .group_by(col(PromptEditorMessage.session_id))
        .subquery()
    )
    list_stmt = (
        select(PromptEditorSession, func.coalesce(msg_counts.c.cnt, 0))
        .outerjoin(msg_counts, col(PromptEditorSession.id) == msg_counts.c.session_id)
        .order_by(col(PromptEditorSession.updated_at).desc())
        .offset(skip)
        .limit(limit)
    )
    if agent_id is not None:
        list_stmt = list_stmt.where(col(PromptEditorSession.agent_id) == agent_id)
    if created_by is not None:
        list_stmt = list_stmt.where(col(PromptEditorSession.created_by) == created_by)

    rows = session.exec(list_stmt).all()
    return [(row[0], row[1]) for row in rows], total


def update_session(
    *,
    session: Session,
    db_session: PromptEditorSession,
    session_in: PromptEditorSessionUpdate,
) -> PromptEditorSession:
    update_data = session_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_session
    db_session.sqlmodel_update(update_data)
    session.add(db_session)
    session.commit()
    session.refresh(db_session)
    return db_session


def delete_session(*, session: Session, db_session: PromptEditorSession) -> None:
    session.delete(db_session)
    session.commit()
