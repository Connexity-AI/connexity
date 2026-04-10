import uuid

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models.enums import PromptEditorSessionStatus
from app.models.prompt_editor import (
    PromptEditorMessage,
    PromptEditorMessageCreate,
    PromptEditorSession,
)


def create_message(
    *, session: Session, message_in: PromptEditorMessageCreate
) -> PromptEditorMessage:
    db_sess = session.get(PromptEditorSession, message_in.session_id)
    if db_sess is None:
        msg = "Prompt editor session not found"
        raise ValueError(msg)
    if db_sess.status != PromptEditorSessionStatus.ACTIVE:
        msg = "Session is not active"
        raise ValueError(msg)

    db_obj = PromptEditorMessage(
        session_id=message_in.session_id,
        role=message_in.role,
        content=message_in.content,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def list_messages(
    *, session: Session, session_id: uuid.UUID, skip: int, limit: int
) -> tuple[list[PromptEditorMessage], int]:
    filters = [col(PromptEditorMessage.session_id) == session_id]
    count_stmt = select(func.count()).select_from(PromptEditorMessage).where(*filters)
    total = session.exec(count_stmt).one()
    list_stmt = (
        select(PromptEditorMessage)
        .where(*filters)
        .order_by(col(PromptEditorMessage.created_at).asc())
        .offset(skip)
        .limit(limit)
    )
    items = list(session.exec(list_stmt).all())
    return items, total
