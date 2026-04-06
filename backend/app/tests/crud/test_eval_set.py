import uuid

import pytest
from sqlmodel import Session

from app import crud
from app.models import EvalSetMemberEntry, EvalSetUpdate
from app.tests.utils.eval import (
    create_test_case_fixture,
    create_test_eval_set,
    eval_set_members,
)


def test_create_eval_set(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    assert eval_set.id is not None
    assert eval_set.name.startswith("test-set-")


def test_create_eval_set_with_test_cases(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(s1.id, s2.id))
    listed_members, count = crud.list_test_cases_in_set(
        session=db, eval_set_id=eval_set.id
    )
    assert count == 2
    assert listed_members[0].test_case_id == s1.id
    assert listed_members[1].test_case_id == s2.id
    assert listed_members[0].repetitions == 1
    assert eval_set.version == 1


def test_create_eval_set_with_invalid_test_case_ids(db: Session) -> None:
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Test cases not found"):
        create_test_eval_set(db, members=eval_set_members(fake_id))


def test_get_eval_set(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    fetched = crud.get_eval_set(session=db, eval_set_id=eval_set.id)
    assert fetched is not None
    assert fetched.id == eval_set.id


def test_list_eval_sets(db: Session) -> None:
    create_test_eval_set(db)
    items, count = crud.list_eval_sets(session=db)
    assert count >= 1


def test_update_eval_set(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    updated = crud.update_eval_set(
        session=db,
        db_eval_set=eval_set,
        eval_set_in=EvalSetUpdate(name="Updated Set"),
    )
    assert updated.name == "Updated Set"


def test_add_test_cases_to_set(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    test_case = create_test_case_fixture(db)
    updated = crud.add_test_cases_to_set(
        session=db,
        db_eval_set=eval_set,
        members=[EvalSetMemberEntry(test_case_id=test_case.id)],
    )
    assert updated.id == eval_set.id
    listed_members, count = crud.list_test_cases_in_set(
        session=db, eval_set_id=eval_set.id
    )
    assert count == 1
    assert listed_members[0].test_case_id == test_case.id


def test_add_invalid_test_case_to_set(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    with pytest.raises(ValueError, match="Test cases not found"):
        crud.add_test_cases_to_set(
            session=db,
            db_eval_set=eval_set,
            members=[EvalSetMemberEntry(test_case_id=uuid.uuid4())],
        )


def test_add_duplicate_test_case_ids_in_request_rejected(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    test_case = create_test_case_fixture(db)
    with pytest.raises(ValueError, match="Duplicate test_case_id"):
        crud.add_test_cases_to_set(
            session=db,
            db_eval_set=eval_set,
            members=[
                EvalSetMemberEntry(test_case_id=test_case.id),
                EvalSetMemberEntry(test_case_id=test_case.id),
            ],
        )


def test_add_test_case_already_in_set_rejected(db: Session) -> None:
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))
    with pytest.raises(ValueError, match="Test cases already in set"):
        crud.add_test_cases_to_set(
            session=db,
            db_eval_set=eval_set,
            members=[EvalSetMemberEntry(test_case_id=test_case.id)],
        )


def test_sum_member_repetitions_in_sets_batch(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    set_a = create_test_eval_set(db, members=eval_set_members(s1.id))
    set_b = create_test_eval_set(db)
    crud.replace_test_cases_in_set(
        session=db,
        db_eval_set=set_a,
        members=[
            EvalSetMemberEntry(test_case_id=s1.id, repetitions=2),
            EvalSetMemberEntry(test_case_id=s2.id, repetitions=3),
        ],
    )
    sums = crud.sum_member_repetitions_in_sets(
        session=db, eval_set_ids=[set_a.id, set_b.id]
    )
    assert sums[set_a.id] == 5
    assert sums[set_b.id] == 0


def test_remove_test_case_from_set(db: Session) -> None:
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))

    updated = crud.remove_test_case_from_set(
        session=db,
        db_eval_set=eval_set,
        test_case_id=test_case.id,
    )
    assert updated.id == eval_set.id
    _, count = crud.list_test_cases_in_set(session=db, eval_set_id=eval_set.id)
    assert count == 0


def test_replace_test_cases_in_set(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(s1.id, s2.id))

    updated = crud.replace_test_cases_in_set(
        session=db,
        db_eval_set=eval_set,
        members=[EvalSetMemberEntry(test_case_id=s3.id, repetitions=2)],
    )
    assert updated.id == eval_set.id
    listed_members, count = crud.list_test_cases_in_set(
        session=db, eval_set_id=eval_set.id
    )
    assert count == 1
    assert listed_members[0].test_case_id == s3.id
    assert listed_members[0].repetitions == 2


def test_replace_with_invalid_test_case_ids(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(s1.id))
    with pytest.raises(ValueError, match="Test cases not found"):
        crud.replace_test_cases_in_set(
            session=db,
            db_eval_set=eval_set,
            members=[EvalSetMemberEntry(test_case_id=uuid.uuid4())],
        )


def test_list_test_cases_in_set_ordered(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(s3.id, s1.id, s2.id))
    listed_members, count = crud.list_test_cases_in_set(
        session=db, eval_set_id=eval_set.id
    )
    assert count == 3
    assert listed_members[0].test_case_id == s3.id
    assert listed_members[1].test_case_id == s1.id
    assert listed_members[2].test_case_id == s2.id


def test_list_test_cases_in_set_paginated(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(s1.id, s2.id, s3.id))

    page1, count = crud.list_test_cases_in_set(
        session=db, eval_set_id=eval_set.id, skip=0, limit=2
    )
    assert count == 3
    assert len(page1) == 2
    assert page1[0].test_case_id == s1.id

    page2, _ = crud.list_test_cases_in_set(
        session=db, eval_set_id=eval_set.id, skip=2, limit=2
    )
    assert len(page2) == 1
    assert page2[0].test_case_id == s3.id


def test_version_increments_on_add(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    assert eval_set.version == 1
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    updated = crud.add_test_cases_to_set(
        session=db,
        db_eval_set=eval_set,
        members=[
            EvalSetMemberEntry(test_case_id=s1.id),
            EvalSetMemberEntry(test_case_id=s2.id),
        ],
    )
    assert updated.version == 2


def test_version_increments_on_remove(db: Session) -> None:
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))
    assert eval_set.version == 1
    updated = crud.remove_test_case_from_set(
        session=db, db_eval_set=eval_set, test_case_id=test_case.id
    )
    assert updated.version == 2


def test_version_not_incremented_on_noop_remove(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    assert eval_set.version == 1
    updated = crud.remove_test_case_from_set(
        session=db, db_eval_set=eval_set, test_case_id=uuid.uuid4()
    )
    assert updated.version == 1


def test_version_increments_on_replace(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(s1.id))
    assert eval_set.version == 1
    updated = crud.replace_test_cases_in_set(
        session=db,
        db_eval_set=eval_set,
        members=[EvalSetMemberEntry(test_case_id=s2.id)],
    )
    assert updated.version == 2


def test_version_increments_multiple_operations(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db)
    assert eval_set.version == 1

    crud.add_test_cases_to_set(
        session=db,
        db_eval_set=eval_set,
        members=[
            EvalSetMemberEntry(test_case_id=s1.id),
            EvalSetMemberEntry(test_case_id=s2.id),
        ],
    )
    crud.replace_test_cases_in_set(
        session=db,
        db_eval_set=eval_set,
        members=[EvalSetMemberEntry(test_case_id=s3.id)],
    )
    updated = crud.remove_test_case_from_set(
        session=db, db_eval_set=eval_set, test_case_id=s3.id
    )
    assert updated.version == 4


def test_version_not_bumped_on_metadata_update(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    assert eval_set.version == 1
    updated = crud.update_eval_set(
        session=db,
        db_eval_set=eval_set,
        eval_set_in=EvalSetUpdate(name="Renamed", description="New desc"),
    )
    assert updated.version == 1


def test_delete_eval_set(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    set_id = eval_set.id
    crud.delete_eval_set(session=db, db_eval_set=eval_set)
    fetched = crud.get_eval_set(session=db, eval_set_id=set_id)
    assert fetched is None


def test_get_test_cases_for_set_returns_active_only(db: Session) -> None:
    active = create_test_case_fixture(db, status="active")
    draft = create_test_case_fixture(db, status="draft")
    archived = create_test_case_fixture(db, status="archived")
    eval_set = create_test_eval_set(
        db, members=eval_set_members(active.id, draft.id, archived.id)
    )
    results = crud.get_test_cases_for_set(session=db, eval_set_id=eval_set.id)
    result_ids = [entry.test_case.id for entry in results]
    assert active.id in result_ids
    assert draft.id not in result_ids
    assert archived.id not in result_ids


def test_get_test_cases_for_set_preserves_order(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(s3.id, s1.id, s2.id))
    results = crud.get_test_cases_for_set(session=db, eval_set_id=eval_set.id)
    assert [e.test_case.id for e in results] == [s3.id, s1.id, s2.id]


def test_get_test_cases_for_set_includes_repetitions(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db)
    crud.replace_test_cases_in_set(
        session=db,
        db_eval_set=eval_set,
        members=[EvalSetMemberEntry(test_case_id=s1.id, repetitions=3)],
    )
    results = crud.get_test_cases_for_set(session=db, eval_set_id=eval_set.id)
    assert len(results) == 1
    assert results[0].repetitions == 3
    assert results[0].position == 0


def test_get_test_cases_for_set_empty(db: Session) -> None:
    eval_set = create_test_eval_set(db)
    results = crud.get_test_cases_for_set(session=db, eval_set_id=eval_set.id)
    assert results == []


def test_sum_member_repetitions_in_set(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db)
    crud.replace_test_cases_in_set(
        session=db,
        db_eval_set=eval_set,
        members=[
            EvalSetMemberEntry(test_case_id=s1.id, repetitions=2),
            EvalSetMemberEntry(test_case_id=s2.id, repetitions=3),
        ],
    )
    total = crud.sum_member_repetitions_in_set(session=db, eval_set_id=eval_set.id)
    assert total == 5


def test_count_test_cases_in_sets_batch(db: Session) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    set_a = create_test_eval_set(db, members=eval_set_members(s1.id, s2.id))
    set_b = create_test_eval_set(db)

    counts = crud.count_test_cases_in_sets(
        session=db, eval_set_ids=[set_a.id, set_b.id]
    )
    assert counts[set_a.id] == 2
    assert counts.get(set_b.id, 0) == 0
