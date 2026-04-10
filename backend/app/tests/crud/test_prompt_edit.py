import uuid

import pytest
from sqlmodel import Session, col, select

from app import crud
from app.models.enums import PromptEditStatus, TurnRole
from app.models.prompt_editor import (
    PromptEdit,
    PromptEditCreate,
    PromptEditorMessageCreate,
)
from app.tests.utils.eval import (
    create_test_agent,
    create_test_prompt_editor_session,
)
from app.tests.utils.user import create_random_user


def test_create_prompt_edits_bulk(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id,
            role=TurnRole.ASSISTANT,
            content="reasoning",
        ),
    )
    edits_in = [
        PromptEditCreate(
            start_line=1,
            end_line=1,
            new_content="a",
            original_content="b",
        ),
        PromptEditCreate(
            start_line=2,
            end_line=3,
            new_content="c",
            original_content="d",
        ),
        PromptEditCreate(
            start_line=5,
            end_line=5,
            new_content="e",
            original_content="f",
        ),
    ]
    created = crud.create_prompt_edits(session=db, message_id=msg.id, edits=edits_in)
    assert len(created) == 3
    assert all(e.status == PromptEditStatus.PENDING for e in created)
    assert {e.start_line for e in created} == {1, 2, 5}


def test_create_prompt_edits_validates_message(db: Session) -> None:
    with pytest.raises(ValueError, match="Message not found"):
        crud.create_prompt_edits(
            session=db,
            message_id=uuid.uuid4(),
            edits=[
                PromptEditCreate(
                    start_line=1,
                    end_line=1,
                    new_content="x",
                    original_content="y",
                )
            ],
        )


def test_list_edits_for_message(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="x"
        ),
    )
    crud.create_prompt_edits(
        session=db,
        message_id=msg.id,
        edits=[
            PromptEditCreate(
                start_line=10,
                end_line=10,
                new_content="n",
                original_content="o",
            ),
            PromptEditCreate(
                start_line=2,
                end_line=2,
                new_content="n",
                original_content="o",
            ),
        ],
    )
    listed = crud.list_prompt_edits_for_message(session=db, message_id=msg.id)
    assert [e.start_line for e in listed] == [2, 10]


def test_update_prompt_edit_status_accept(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="x"
        ),
    )
    edits = crud.create_prompt_edits(
        session=db,
        message_id=msg.id,
        edits=[
            PromptEditCreate(
                start_line=1,
                end_line=1,
                new_content="n",
                original_content="o",
            )
        ],
    )
    updated = crud.update_prompt_edit_status(
        session=db,
        edit_id=edits[0].id,
        status=PromptEditStatus.ACCEPTED,
    )
    assert updated.status == PromptEditStatus.ACCEPTED


def test_update_prompt_edit_status_decline(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="x"
        ),
    )
    edits = crud.create_prompt_edits(
        session=db,
        message_id=msg.id,
        edits=[
            PromptEditCreate(
                start_line=1,
                end_line=1,
                new_content="n",
                original_content="o",
            )
        ],
    )
    updated = crud.update_prompt_edit_status(
        session=db,
        edit_id=edits[0].id,
        status=PromptEditStatus.DECLINED,
    )
    assert updated.status == PromptEditStatus.DECLINED


def test_update_prompt_edit_status_not_pending(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="x"
        ),
    )
    edits = crud.create_prompt_edits(
        session=db,
        message_id=msg.id,
        edits=[
            PromptEditCreate(
                start_line=1,
                end_line=1,
                new_content="n",
                original_content="o",
            )
        ],
    )
    crud.update_prompt_edit_status(
        session=db,
        edit_id=edits[0].id,
        status=PromptEditStatus.ACCEPTED,
    )
    with pytest.raises(ValueError, match="not pending"):
        crud.update_prompt_edit_status(
            session=db,
            edit_id=edits[0].id,
            status=PromptEditStatus.DECLINED,
        )


def test_update_prompt_edit_status_not_found(db: Session) -> None:
    with pytest.raises(ValueError, match="Edit not found"):
        crud.update_prompt_edit_status(
            session=db,
            edit_id=uuid.uuid4(),
            status=PromptEditStatus.ACCEPTED,
        )


def test_batch_update_with_specific_ids(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="x"
        ),
    )
    edits = crud.create_prompt_edits(
        session=db,
        message_id=msg.id,
        edits=[
            PromptEditCreate(
                start_line=1,
                end_line=1,
                new_content="a",
                original_content="b",
            ),
            PromptEditCreate(
                start_line=2,
                end_line=2,
                new_content="c",
                original_content="d",
            ),
            PromptEditCreate(
                start_line=3,
                end_line=3,
                new_content="e",
                original_content="f",
            ),
        ],
    )
    updated = crud.batch_update_prompt_edit_status(
        session=db,
        message_id=msg.id,
        status=PromptEditStatus.ACCEPTED,
        edit_ids=[edits[0].id, edits[2].id],
    )
    assert len(updated) == 2
    assert {e.id for e in updated} == {edits[0].id, edits[2].id}
    remaining = crud.list_prompt_edits_for_message(session=db, message_id=msg.id)
    by_id = {e.id: e for e in remaining}
    assert by_id[edits[0].id].status == PromptEditStatus.ACCEPTED
    assert by_id[edits[1].id].status == PromptEditStatus.PENDING
    assert by_id[edits[2].id].status == PromptEditStatus.ACCEPTED


def test_batch_update_all_pending(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="x"
        ),
    )
    crud.create_prompt_edits(
        session=db,
        message_id=msg.id,
        edits=[
            PromptEditCreate(
                start_line=1,
                end_line=1,
                new_content="a",
                original_content="b",
            ),
            PromptEditCreate(
                start_line=2,
                end_line=2,
                new_content="c",
                original_content="d",
            ),
        ],
    )
    updated = crud.batch_update_prompt_edit_status(
        session=db,
        message_id=msg.id,
        status=PromptEditStatus.DECLINED,
        edit_ids=None,
    )
    assert len(updated) == 2
    assert all(e.status == PromptEditStatus.DECLINED for e in updated)


def test_batch_update_skips_non_pending(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="x"
        ),
    )
    edits = crud.create_prompt_edits(
        session=db,
        message_id=msg.id,
        edits=[
            PromptEditCreate(
                start_line=1,
                end_line=1,
                new_content="a",
                original_content="b",
            ),
            PromptEditCreate(
                start_line=2,
                end_line=2,
                new_content="c",
                original_content="d",
            ),
            PromptEditCreate(
                start_line=3,
                end_line=3,
                new_content="e",
                original_content="f",
            ),
        ],
    )
    crud.update_prompt_edit_status(
        session=db,
        edit_id=edits[0].id,
        status=PromptEditStatus.ACCEPTED,
    )
    updated = crud.batch_update_prompt_edit_status(
        session=db,
        message_id=msg.id,
        status=PromptEditStatus.DECLINED,
        edit_ids=None,
    )
    assert len(updated) == 2
    by_id = {
        e.id: e
        for e in crud.list_prompt_edits_for_message(session=db, message_id=msg.id)
    }
    assert by_id[edits[0].id].status == PromptEditStatus.ACCEPTED
    assert by_id[edits[1].id].status == PromptEditStatus.DECLINED
    assert by_id[edits[2].id].status == PromptEditStatus.DECLINED


def test_batch_update_empty_edit_ids(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="x"
        ),
    )
    crud.create_prompt_edits(
        session=db,
        message_id=msg.id,
        edits=[
            PromptEditCreate(
                start_line=1,
                end_line=1,
                new_content="a",
                original_content="b",
            ),
        ],
    )
    updated = crud.batch_update_prompt_edit_status(
        session=db,
        message_id=msg.id,
        status=PromptEditStatus.ACCEPTED,
        edit_ids=[],
    )
    assert updated == []
    listed = crud.list_prompt_edits_for_message(session=db, message_id=msg.id)
    assert listed[0].status == PromptEditStatus.PENDING


def test_cascade_delete_message(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="x"
        ),
    )
    crud.create_prompt_edits(
        session=db,
        message_id=msg.id,
        edits=[
            PromptEditCreate(
                start_line=1,
                end_line=1,
                new_content="a",
                original_content="b",
            ),
        ],
    )
    db.delete(msg)
    db.commit()
    remaining = db.exec(
        select(PromptEdit).where(col(PromptEdit.message_id) == msg.id)
    ).all()
    assert len(remaining) == 0


def test_cascade_delete_session(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="x"
        ),
    )
    crud.create_prompt_edits(
        session=db,
        message_id=msg.id,
        edits=[
            PromptEditCreate(
                start_line=1,
                end_line=1,
                new_content="a",
                original_content="b",
            ),
        ],
    )
    edit_id = crud.list_prompt_edits_for_message(session=db, message_id=msg.id)[0].id

    crud.delete_prompt_editor_session(session=db, db_session=s)

    assert db.get(PromptEdit, edit_id) is None
