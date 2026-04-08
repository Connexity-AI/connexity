import uuid

import pytest
from sqlmodel import Session

from app import crud
from app.models import PromptEditorSessionUpdate
from app.models.enums import PromptEditorSessionStatus, PromptSuggestionStatus, TurnRole
from app.models.prompt_editor import PromptEditorMessageCreate
from app.tests.utils.eval import (
    create_test_agent,
    create_test_prompt_editor_session,
)
from app.tests.utils.user import create_random_user


def test_create_message(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg_in = PromptEditorMessageCreate(
        session_id=s.id,
        role=TurnRole.USER,
        content="Hi",
    )
    m = crud.create_prompt_editor_message(session=db, message_in=msg_in)
    assert m.content == "Hi"
    assert m.session_id == s.id
    assert m.suggestion_status is None


def test_create_message_archived_session(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    crud.update_prompt_editor_session(
        session=db,
        db_session=s,
        session_in=PromptEditorSessionUpdate(status=PromptEditorSessionStatus.ARCHIVED),
    )
    msg_in = PromptEditorMessageCreate(
        session_id=s.id,
        role=TurnRole.USER,
        content="nope",
    )
    with pytest.raises(ValueError, match="Session is not active"):
        crud.create_prompt_editor_message(session=db, message_in=msg_in)


def test_create_message_with_suggestion(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    msg_in = PromptEditorMessageCreate(
        session_id=s.id,
        role=TurnRole.ASSISTANT,
        content="Here is a suggestion",
        prompt_suggestion="You are a helpful bot.",
    )
    m = crud.create_prompt_editor_message(session=db, message_in=msg_in)
    assert m.prompt_suggestion == "You are a helpful bot."
    assert m.suggestion_status == PromptSuggestionStatus.PENDING


def test_create_message_invalid_session(db: Session) -> None:
    msg_in = PromptEditorMessageCreate(
        session_id=uuid.uuid4(),
        role=TurnRole.USER,
        content="x",
    )
    with pytest.raises(ValueError, match="Prompt editor session not found"):
        crud.create_prompt_editor_message(session=db, message_in=msg_in)


def test_list_messages_chronological(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    m1 = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.USER, content="first"
        ),
    )
    m2 = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="second"
        ),
    )
    m3 = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.USER, content="third"
        ),
    )

    items, count = crud.list_prompt_editor_messages(
        session=db, session_id=s.id, skip=0, limit=50
    )
    assert count == 3
    assert [x.id for x in items] == [m1.id, m2.id, m3.id]


def test_list_messages_pagination(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    for i in range(3):
        crud.create_prompt_editor_message(
            session=db,
            message_in=PromptEditorMessageCreate(
                session_id=s.id, role=TurnRole.USER, content=f"m{i}"
            ),
        )

    page, total = crud.list_prompt_editor_messages(
        session=db, session_id=s.id, skip=0, limit=2
    )
    assert total == 3
    assert len(page) == 2


def test_update_suggestion_status_accept(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    m = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id,
            role=TurnRole.ASSISTANT,
            content="try this",
            prompt_suggestion="new prompt",
        ),
    )
    updated = crud.update_prompt_editor_suggestion_status(
        session=db,
        message_id=m.id,
        status=PromptSuggestionStatus.ACCEPTED,
    )
    assert updated.suggestion_status == PromptSuggestionStatus.ACCEPTED


def test_update_suggestion_status_decline(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    m = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id,
            role=TurnRole.ASSISTANT,
            content="try this",
            prompt_suggestion="new prompt",
        ),
    )
    updated = crud.update_prompt_editor_suggestion_status(
        session=db,
        message_id=m.id,
        status=PromptSuggestionStatus.DECLINED,
    )
    assert updated.suggestion_status == PromptSuggestionStatus.DECLINED


def test_update_suggestion_status_no_suggestion(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    m = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.USER, content="plain"
        ),
    )
    with pytest.raises(ValueError, match="no prompt suggestion"):
        crud.update_prompt_editor_suggestion_status(
            session=db,
            message_id=m.id,
            status=PromptSuggestionStatus.ACCEPTED,
        )


def test_update_suggestion_status_already_accepted(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    m = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id,
            role=TurnRole.ASSISTANT,
            content="try this",
            prompt_suggestion="new prompt",
        ),
    )
    crud.update_prompt_editor_suggestion_status(
        session=db,
        message_id=m.id,
        status=PromptSuggestionStatus.ACCEPTED,
    )
    with pytest.raises(ValueError, match="not pending"):
        crud.update_prompt_editor_suggestion_status(
            session=db,
            message_id=m.id,
            status=PromptSuggestionStatus.DECLINED,
        )
