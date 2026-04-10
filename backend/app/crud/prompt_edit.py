import uuid

from sqlmodel import Session, col, select

from app.models.enums import PromptEditStatus
from app.models.prompt_editor import PromptEdit, PromptEditCreate, PromptEditorMessage


def create_prompt_edits(
    *,
    session: Session,
    message_id: uuid.UUID,
    edits: list[PromptEditCreate],
) -> list[PromptEdit]:
    db_msg = session.get(PromptEditorMessage, message_id)
    if db_msg is None:
        msg = "Message not found"
        raise ValueError(msg)

    created: list[PromptEdit] = []
    for edit_in in edits:
        row = PromptEdit(
            message_id=message_id,
            start_line=edit_in.start_line,
            end_line=edit_in.end_line,
            new_content=edit_in.new_content,
            original_content=edit_in.original_content,
            status=PromptEditStatus.PENDING,
        )
        session.add(row)
        created.append(row)
    session.commit()
    for row in created:
        session.refresh(row)
    return created


def list_prompt_edits_for_message(
    *, session: Session, message_id: uuid.UUID
) -> list[PromptEdit]:
    stmt = (
        select(PromptEdit)
        .where(col(PromptEdit.message_id) == message_id)
        .order_by(col(PromptEdit.start_line).asc())
    )
    return list(session.exec(stmt).all())


def update_prompt_edit_status(
    *,
    session: Session,
    edit_id: uuid.UUID,
    status: PromptEditStatus,
) -> PromptEdit:
    db_edit = session.get(PromptEdit, edit_id)
    if db_edit is None:
        msg = "Edit not found"
        raise ValueError(msg)
    if db_edit.status != PromptEditStatus.PENDING:
        msg = "Edit status is not pending"
        raise ValueError(msg)

    db_edit.status = status
    session.add(db_edit)
    session.commit()
    session.refresh(db_edit)
    return db_edit


def batch_update_prompt_edit_status(
    *,
    session: Session,
    message_id: uuid.UUID,
    status: PromptEditStatus,
    edit_ids: list[uuid.UUID] | None = None,
) -> list[PromptEdit]:
    db_msg = session.get(PromptEditorMessage, message_id)
    if db_msg is None:
        msg = "Message not found"
        raise ValueError(msg)

    if edit_ids is not None and len(edit_ids) == 0:
        return []

    stmt = select(PromptEdit).where(col(PromptEdit.message_id) == message_id)
    if edit_ids is not None:
        stmt = stmt.where(col(PromptEdit.id).in_(edit_ids))
    candidates = list(session.exec(stmt).all())

    updated: list[PromptEdit] = []
    for row in candidates:
        if row.status != PromptEditStatus.PENDING:
            continue
        row.status = status
        session.add(row)
        updated.append(row)

    session.commit()
    for row in updated:
        session.refresh(row)
    return updated
