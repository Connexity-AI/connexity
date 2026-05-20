import uuid

import pytest
from sqlmodel import Session

from app import crud
from app.models import EvalConfigCreate, EvalConfigMemberEntry, EvalConfigUpdate
from app.models.enums import RunMode
from app.models.schemas import RunConfig, SttConfig, TtsConfig, UserSimulatorConfig
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_eval_config,
    eval_config_members,
)


def test_create_eval_config(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    assert eval_config.id is not None
    assert eval_config.name.startswith("test-config-")


def test_create_eval_config_with_test_cases(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(s1.id, s2.id))
    listed_members, count = crud.list_test_cases_in_config(
        session=db, eval_config_id=eval_config.id
    )
    assert count == 2
    assert listed_members[0].test_case_id == s1.id
    assert listed_members[1].test_case_id == s2.id
    assert listed_members[0].repetitions == 1
    assert eval_config.version == 1


def test_create_eval_config_with_invalid_test_case_ids(db: Session) -> None:
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Test cases not found"):
        create_test_eval_config(db, members=eval_config_members(fake_id))


def test_get_eval_config(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    fetched = crud.get_eval_config(session=db, eval_config_id=eval_config.id)
    assert fetched is not None
    assert fetched.id == eval_config.id


def test_list_eval_configs(db: Session) -> None:
    create_test_eval_config(db)
    items, count = crud.list_eval_configs(session=db)
    assert count >= 1


def test_update_eval_config(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    updated = crud.update_eval_config(
        session=db,
        db_eval_config=eval_config,
        eval_config_in=EvalConfigUpdate(name="Updated Config"),
    )
    assert updated.name == "Updated Config"


def test_add_test_cases_to_config(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    test_case = create_test_case_fixture(db)
    updated = crud.add_test_cases_to_config(
        session=db,
        db_eval_config=eval_config,
        members=[EvalConfigMemberEntry(test_case_id=test_case.id)],
    )
    assert updated.id == eval_config.id
    listed_members, count = crud.list_test_cases_in_config(
        session=db, eval_config_id=eval_config.id
    )
    assert count == 1
    assert listed_members[0].test_case_id == test_case.id


def test_add_invalid_test_case_to_config(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    with pytest.raises(ValueError, match="Test cases not found"):
        crud.add_test_cases_to_config(
            session=db,
            db_eval_config=eval_config,
            members=[EvalConfigMemberEntry(test_case_id=uuid.uuid4())],
        )


def test_add_duplicate_test_case_ids_in_request_rejected(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    test_case = create_test_case_fixture(db)
    with pytest.raises(ValueError, match="Duplicate test_case_id"):
        crud.add_test_cases_to_config(
            session=db,
            db_eval_config=eval_config,
            members=[
                EvalConfigMemberEntry(test_case_id=test_case.id),
                EvalConfigMemberEntry(test_case_id=test_case.id),
            ],
        )


def test_add_test_case_already_in_config_rejected(db: Session) -> None:
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(test_case.id))
    with pytest.raises(ValueError, match="Test cases already in config"):
        crud.add_test_cases_to_config(
            session=db,
            db_eval_config=eval_config,
            members=[EvalConfigMemberEntry(test_case_id=test_case.id)],
        )


def test_sum_member_repetitions_in_configs_batch(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    config_a = create_test_eval_config(db, members=eval_config_members(s1.id))
    config_b = create_test_eval_config(db)
    crud.replace_test_cases_in_config(
        session=db,
        db_eval_config=config_a,
        members=[
            EvalConfigMemberEntry(test_case_id=s1.id, repetitions=2),
            EvalConfigMemberEntry(test_case_id=s2.id, repetitions=3),
        ],
    )
    sums = crud.sum_member_repetitions_in_configs(
        session=db, eval_config_ids=[config_a.id, config_b.id]
    )
    assert sums[config_a.id] == 5
    assert sums[config_b.id] == 0


def test_remove_test_case_from_config(db: Session) -> None:
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(test_case.id))

    updated = crud.remove_test_case_from_config(
        session=db,
        db_eval_config=eval_config,
        test_case_id=test_case.id,
    )
    assert updated.id == eval_config.id
    _, count = crud.list_test_cases_in_config(session=db, eval_config_id=eval_config.id)
    assert count == 0


def test_replace_test_cases_in_config(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(s1.id, s2.id))

    updated = crud.replace_test_cases_in_config(
        session=db,
        db_eval_config=eval_config,
        members=[EvalConfigMemberEntry(test_case_id=s3.id, repetitions=2)],
    )
    assert updated.id == eval_config.id
    listed_members, count = crud.list_test_cases_in_config(
        session=db, eval_config_id=eval_config.id
    )
    assert count == 1
    assert listed_members[0].test_case_id == s3.id
    assert listed_members[0].repetitions == 2


def test_replace_with_invalid_test_case_ids(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(s1.id))
    with pytest.raises(ValueError, match="Test cases not found"):
        crud.replace_test_cases_in_config(
            session=db,
            db_eval_config=eval_config,
            members=[EvalConfigMemberEntry(test_case_id=uuid.uuid4())],
        )


def test_list_test_cases_in_config_ordered(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, members=eval_config_members(s3.id, s1.id, s2.id)
    )
    listed_members, count = crud.list_test_cases_in_config(
        session=db, eval_config_id=eval_config.id
    )
    assert count == 3
    assert listed_members[0].test_case_id == s3.id
    assert listed_members[1].test_case_id == s1.id
    assert listed_members[2].test_case_id == s2.id


def test_list_test_cases_in_config_paginated(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, members=eval_config_members(s1.id, s2.id, s3.id)
    )

    page1, count = crud.list_test_cases_in_config(
        session=db, eval_config_id=eval_config.id, skip=0, limit=2
    )
    assert count == 3
    assert len(page1) == 2
    assert page1[0].test_case_id == s1.id

    page2, _ = crud.list_test_cases_in_config(
        session=db, eval_config_id=eval_config.id, skip=2, limit=2
    )
    assert len(page2) == 1
    assert page2[0].test_case_id == s3.id


def test_version_increments_on_add(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    assert eval_config.version == 1
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    updated = crud.add_test_cases_to_config(
        session=db,
        db_eval_config=eval_config,
        members=[
            EvalConfigMemberEntry(test_case_id=s1.id),
            EvalConfigMemberEntry(test_case_id=s2.id),
        ],
    )
    assert updated.version == 2


def test_version_increments_on_remove(db: Session) -> None:
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(test_case.id))
    assert eval_config.version == 1
    updated = crud.remove_test_case_from_config(
        session=db, db_eval_config=eval_config, test_case_id=test_case.id
    )
    assert updated.version == 2


def test_version_not_incremented_on_noop_remove(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    assert eval_config.version == 1
    updated = crud.remove_test_case_from_config(
        session=db, db_eval_config=eval_config, test_case_id=uuid.uuid4()
    )
    assert updated.version == 1


def test_version_increments_on_replace(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(s1.id))
    assert eval_config.version == 1
    updated = crud.replace_test_cases_in_config(
        session=db,
        db_eval_config=eval_config,
        members=[EvalConfigMemberEntry(test_case_id=s2.id)],
    )
    assert updated.version == 2


def test_version_increments_multiple_operations(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db)
    assert eval_config.version == 1

    crud.add_test_cases_to_config(
        session=db,
        db_eval_config=eval_config,
        members=[
            EvalConfigMemberEntry(test_case_id=s1.id),
            EvalConfigMemberEntry(test_case_id=s2.id),
        ],
    )
    crud.replace_test_cases_in_config(
        session=db,
        db_eval_config=eval_config,
        members=[EvalConfigMemberEntry(test_case_id=s3.id)],
    )
    updated = crud.remove_test_case_from_config(
        session=db, db_eval_config=eval_config, test_case_id=s3.id
    )
    assert updated.version == 4


def test_version_not_bumped_on_metadata_update(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    assert eval_config.version == 1
    updated = crud.update_eval_config(
        session=db,
        db_eval_config=eval_config,
        eval_config_in=EvalConfigUpdate(name="Renamed", description="New desc"),
    )
    assert updated.version == 1


def test_delete_eval_config(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    config_id = eval_config.id
    crud.delete_eval_config(session=db, db_eval_config=eval_config)
    fetched = crud.get_eval_config(session=db, eval_config_id=config_id)
    assert fetched is None


def test_delete_eval_config_is_soft(db: Session) -> None:
    """delete_eval_config stamps deleted_at and excludes the row from list/get."""
    eval_config = create_test_eval_config(db)
    config_id = eval_config.id
    crud.delete_eval_config(session=db, db_eval_config=eval_config)

    listed, count = crud.list_eval_configs(session=db, agent_id=eval_config.agent_id)
    assert all(item.id != config_id for item in listed)
    assert count == 0

    still_there = crud.get_eval_config(
        session=db, eval_config_id=config_id, include_deleted=True
    )
    assert still_there is not None
    assert still_there.deleted_at is not None


def test_get_test_cases_for_config_returns_active_only(db: Session) -> None:
    active = create_test_case_fixture(db, status="active")
    draft = create_test_case_fixture(db, status="draft")
    archived = create_test_case_fixture(db, status="archived")
    eval_config = create_test_eval_config(
        db, members=eval_config_members(active.id, draft.id, archived.id)
    )
    results = crud.get_test_cases_for_config(session=db, eval_config_id=eval_config.id)
    result_ids = [entry.test_case.id for entry in results]
    assert active.id in result_ids
    assert draft.id not in result_ids
    assert archived.id not in result_ids


def test_get_test_cases_for_config_preserves_order(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, members=eval_config_members(s3.id, s1.id, s2.id)
    )
    results = crud.get_test_cases_for_config(session=db, eval_config_id=eval_config.id)
    assert [e.test_case.id for e in results] == [s3.id, s1.id, s2.id]


def test_get_test_cases_for_config_includes_repetitions(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db)
    crud.replace_test_cases_in_config(
        session=db,
        db_eval_config=eval_config,
        members=[EvalConfigMemberEntry(test_case_id=s1.id, repetitions=3)],
    )
    results = crud.get_test_cases_for_config(session=db, eval_config_id=eval_config.id)
    assert len(results) == 1
    assert results[0].repetitions == 3
    assert results[0].position == 0


def test_get_test_cases_for_config_empty(db: Session) -> None:
    eval_config = create_test_eval_config(db)
    results = crud.get_test_cases_for_config(session=db, eval_config_id=eval_config.id)
    assert results == []


def test_sum_member_repetitions_in_config(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db)
    crud.replace_test_cases_in_config(
        session=db,
        db_eval_config=eval_config,
        members=[
            EvalConfigMemberEntry(test_case_id=s1.id, repetitions=2),
            EvalConfigMemberEntry(test_case_id=s2.id, repetitions=3),
        ],
    )
    total = crud.sum_member_repetitions_in_config(
        session=db, eval_config_id=eval_config.id
    )
    assert total == 5


def test_count_test_cases_in_configs_batch(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    config_a = create_test_eval_config(db, members=eval_config_members(s1.id, s2.id))
    config_b = create_test_eval_config(db)

    counts = crud.count_test_cases_in_configs(
        session=db, eval_config_ids=[config_a.id, config_b.id]
    )
    assert counts[config_a.id] == 2
    assert counts.get(config_b.id, 0) == 0


def test_create_eval_config_voice_mode(db: Session) -> None:
    agent = create_test_agent(db)
    voice_config = RunConfig(
        mode=RunMode.VOICE,
        agent_phone_number="+15551234567",
        user_simulator=UserSimulatorConfig(
            stt=SttConfig(provider="deepgram", model="nova-3-general"),
            tts=TtsConfig(
                provider="openai",
                model="gpt-4o-mini-tts",
                voice_id="nova",
            ),
        ),
    )
    created = crud.create_eval_config(
        session=db,
        eval_config_in=EvalConfigCreate(
            name=f"voice-config-{uuid.uuid4().hex[:8]}",
            agent_id=agent.id,
            config=voice_config,
        ),
    )
    parsed = RunConfig.model_validate(created.config)
    assert parsed.mode == RunMode.VOICE
    assert parsed.agent_phone_number == "+15551234567"
    assert parsed.user_simulator is not None
    assert parsed.user_simulator.stt is not None
    assert parsed.user_simulator.tts is not None
