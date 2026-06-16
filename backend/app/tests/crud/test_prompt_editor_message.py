import uuid

import pytest
from sqlmodel import Session

from app import crud
from app.models import PromptEditorSessionUpdate
from app.models.enums import PromptEditorSessionStatus, TurnRole
from app.models.prompt_editor import PromptEditorMessageCreate
from app.tests.utils.eval import (
    create_test_agent,
    create_test_prompt_editor_session,
    get_test_company_id,
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
    m = crud.create_prompt_editor_message(
        session=db, message_in=msg_in, company_id=get_test_company_id(db)
    )
    assert m.content == "Hi"
    assert m.session_id == s.id
    assert m.tool_calls is None


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
        crud.create_prompt_editor_message(
            session=db, message_in=msg_in, company_id=get_test_company_id(db)
        )


def test_create_message_with_tool_calls(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    tc = [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "edit_prompt",
                "arguments": '{"start_line": 1, "end_line": 1, "new_content": "x"}',
            },
        }
    ]
    msg_in = PromptEditorMessageCreate(
        session_id=s.id,
        role=TurnRole.ASSISTANT,
        content="Here is a suggestion",
        tool_calls=tc,
    )
    m = crud.create_prompt_editor_message(
        session=db, message_in=msg_in, company_id=get_test_company_id(db)
    )
    assert m.tool_calls == tc


def test_create_message_invalid_session(db: Session) -> None:
    msg_in = PromptEditorMessageCreate(
        session_id=uuid.uuid4(),
        role=TurnRole.USER,
        content="x",
    )
    with pytest.raises(ValueError, match="Prompt editor session not found"):
        crud.create_prompt_editor_message(
            session=db, message_in=msg_in, company_id=get_test_company_id(db)
        )


def test_list_messages_chronological(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    m1 = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.USER, content="first"
        ),
        company_id=get_test_company_id(db),
    )
    m2 = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.ASSISTANT, content="second"
        ),
        company_id=get_test_company_id(db),
    )
    m3 = crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=s.id, role=TurnRole.USER, content="third"
        ),
        company_id=get_test_company_id(db),
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
            company_id=get_test_company_id(db),
        )

    page, total = crud.list_prompt_editor_messages(
        session=db, session_id=s.id, skip=0, limit=2
    )
    assert total == 3
    assert len(page) == 2
