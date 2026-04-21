import uuid

import pytest
from sqlmodel import Session, col, select

from app import crud
from app.models import (
    PromptEditorSessionCreate,
    PromptEditorSessionStatus,
    PromptEditorSessionUpdate,
)
from app.models.prompt_editor import PromptEditorMessage
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_eval_config,
    create_test_platform_agent,
    create_test_prompt_editor_message,
    create_test_prompt_editor_session,
    create_test_run,
    eval_config_members,
)
from app.tests.utils.user import create_random_user


def test_create_session(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    session_in = PromptEditorSessionCreate(
        agent_id=agent.id,
        title="My session",
    )
    s = crud.create_prompt_editor_session(
        session=db, session_in=session_in, created_by=user.id
    )
    assert s.title == "My session"
    assert s.agent_id == agent.id
    assert s.created_by == user.id
    assert s.status == PromptEditorSessionStatus.ACTIVE


def test_create_session_auto_title(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    session_in = PromptEditorSessionCreate(agent_id=agent.id, title=None)
    s = crud.create_prompt_editor_session(
        session=db, session_in=session_in, created_by=user.id
    )
    assert s.title is not None
    assert s.title.startswith("Session ")


def test_create_session_base_prompt_from_platform_agent(db: Session) -> None:
    agent = create_test_platform_agent(db, system_prompt="Hello from published row")
    user = create_random_user(db)
    session_in = PromptEditorSessionCreate(agent_id=agent.id)
    s = crud.create_prompt_editor_session(
        session=db, session_in=session_in, created_by=user.id
    )
    assert s.base_prompt == "Hello from published row"
    assert s.edited_prompt is None


def test_update_session_edited_prompt(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    updated = crud.update_prompt_editor_session_edited_prompt(
        session=db,
        db_session=s,
        edited_prompt="new prompt text",
    )
    assert updated.edited_prompt == "new prompt text"


def test_update_session_base_prompt(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    updated = crud.update_prompt_editor_session_base_prompt(
        session=db,
        db_session=s,
        base_prompt="saved draft text",
    )
    assert updated.base_prompt == "saved draft text"


def test_create_session_with_run_id(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    tc = create_test_case_fixture(session=db, agent_id=agent.id)
    es = create_test_eval_config(
        session=db, agent_id=agent.id, members=eval_config_members(tc.id)
    )
    run = create_test_run(db, agent_id=agent.id, eval_config_id=es.id)

    session_in = PromptEditorSessionCreate(
        agent_id=agent.id,
        title="With run",
        run_id=run.id,
    )
    s = crud.create_prompt_editor_session(
        session=db, session_in=session_in, created_by=user.id
    )
    assert s.run_id == run.id


def test_create_session_invalid_agent(db: Session) -> None:
    user = create_random_user(db)
    session_in = PromptEditorSessionCreate(
        agent_id=uuid.uuid4(),
        title="x",
    )
    with pytest.raises(ValueError, match="Agent not found"):
        crud.create_prompt_editor_session(
            session=db, session_in=session_in, created_by=user.id
        )


def test_create_session_run_id_wrong_agent(db: Session) -> None:
    agent_a = create_test_agent(db)
    agent_b = create_test_agent(db)
    user = create_random_user(db)
    tc = create_test_case_fixture(session=db, agent_id=agent_a.id)
    es = create_test_eval_config(
        session=db, agent_id=agent_a.id, members=eval_config_members(tc.id)
    )
    run = create_test_run(db, agent_id=agent_a.id, eval_config_id=es.id)

    session_in = PromptEditorSessionCreate(
        agent_id=agent_b.id,
        run_id=run.id,
    )
    with pytest.raises(ValueError, match="Run does not belong to agent"):
        crud.create_prompt_editor_session(
            session=db, session_in=session_in, created_by=user.id
        )


def test_get_session(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    created = create_test_prompt_editor_session(
        db, agent_id=agent.id, created_by=user.id
    )
    fetched = crud.get_prompt_editor_session(session=db, session_id=created.id)
    assert fetched is not None
    assert fetched.id == created.id


def test_get_session_not_found(db: Session) -> None:
    assert crud.get_prompt_editor_session(session=db, session_id=uuid.uuid4()) is None


def test_list_sessions(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    rows, count = crud.list_prompt_editor_sessions(
        session=db,
        agent_id=None,
        created_by=None,
        skip=0,
        limit=100,
    )
    assert count >= 2
    assert len(rows) >= 2
    # Each row is (session, message_count)
    for _s, msg_count in rows:
        assert isinstance(msg_count, int)


def test_list_sessions_filter_by_agent(db: Session) -> None:
    agent_a = create_test_agent(db)
    agent_b = create_test_agent(db)
    user = create_random_user(db)
    create_test_prompt_editor_session(db, agent_id=agent_a.id, created_by=user.id)
    create_test_prompt_editor_session(db, agent_id=agent_b.id, created_by=user.id)

    rows, count = crud.list_prompt_editor_sessions(
        session=db,
        agent_id=agent_a.id,
        created_by=None,
        skip=0,
        limit=100,
    )
    assert count >= 1
    assert all(s.agent_id == agent_a.id for s, _ in rows)


def test_list_sessions_filter_by_created_by(db: Session) -> None:
    agent = create_test_agent(db)
    user_a = create_random_user(db)
    user_b = create_random_user(db)
    create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user_a.id)
    create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user_b.id)

    rows, count = crud.list_prompt_editor_sessions(
        session=db,
        agent_id=None,
        created_by=user_a.id,
        skip=0,
        limit=100,
    )
    assert count >= 1
    assert all(s.created_by == user_a.id for s, _ in rows)


def test_list_sessions_ordering(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    older = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    newer = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)

    rows, _ = crud.list_prompt_editor_sessions(
        session=db,
        agent_id=agent.id,
        created_by=user.id,
        skip=0,
        limit=10,
    )
    ours = [s for s, _ in rows if s.id in (older.id, newer.id)]
    assert ours[0].id == newer.id
    assert ours[1].id == older.id

    crud.update_prompt_editor_session(
        session=db,
        db_session=older,
        session_in=PromptEditorSessionUpdate(title="bump"),
    )
    rows2, _ = crud.list_prompt_editor_sessions(
        session=db,
        agent_id=agent.id,
        created_by=user.id,
        skip=0,
        limit=10,
    )
    ours2 = [s for s, _ in rows2 if s.id in (older.id, newer.id)]
    assert ours2[0].id == older.id
    assert ours2[1].id == newer.id


def test_update_session_title(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    updated = crud.update_prompt_editor_session(
        session=db,
        db_session=s,
        session_in=PromptEditorSessionUpdate(title="Renamed"),
    )
    assert updated.title == "Renamed"


def test_update_session_status(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    updated = crud.update_prompt_editor_session(
        session=db,
        db_session=s,
        session_in=PromptEditorSessionUpdate(status=PromptEditorSessionStatus.ARCHIVED),
    )
    assert updated.status == PromptEditorSessionStatus.ARCHIVED


def test_delete_session_cascades_messages(db: Session) -> None:
    agent = create_test_agent(db)
    user = create_random_user(db)
    s = create_test_prompt_editor_session(db, agent_id=agent.id, created_by=user.id)
    create_test_prompt_editor_message(db, s.id)
    create_test_prompt_editor_message(db, s.id)

    crud.delete_prompt_editor_session(session=db, db_session=s)

    assert crud.get_prompt_editor_session(session=db, session_id=s.id) is None
    remaining = db.exec(
        select(PromptEditorMessage).where(col(PromptEditorMessage.session_id) == s.id)
    ).all()
    assert len(remaining) == 0
