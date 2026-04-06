import uuid

import pytest
from sqlmodel import Session

from app import crud
from app.models import ScenarioSetMemberEntry, ScenarioSetUpdate
from app.tests.utils.eval import (
    create_test_scenario,
    create_test_scenario_set,
    scenario_set_members,
)


def test_create_scenario_set(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    assert scenario_set.id is not None
    assert scenario_set.name.startswith("test-set-")


def test_create_scenario_set_with_scenarios(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(s1.id, s2.id)
    )
    scenarios, count = crud.list_scenarios_in_set(
        session=db, scenario_set_id=scenario_set.id
    )
    assert count == 2
    assert scenarios[0].scenario_id == s1.id
    assert scenarios[1].scenario_id == s2.id
    assert scenarios[0].repetitions == 1
    assert scenario_set.version == 1


def test_create_scenario_set_with_invalid_scenario_ids(db: Session) -> None:
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Scenarios not found"):
        create_test_scenario_set(db, members=scenario_set_members(fake_id))


def test_get_scenario_set(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    fetched = crud.get_scenario_set(session=db, scenario_set_id=scenario_set.id)
    assert fetched is not None
    assert fetched.id == scenario_set.id


def test_list_scenario_sets(db: Session) -> None:
    create_test_scenario_set(db)
    items, count = crud.list_scenario_sets(session=db)
    assert count >= 1


def test_update_scenario_set(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    updated = crud.update_scenario_set(
        session=db,
        db_scenario_set=scenario_set,
        scenario_set_in=ScenarioSetUpdate(name="Updated Set"),
    )
    assert updated.name == "Updated Set"


def test_add_scenarios_to_set(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    scenario = create_test_scenario(db)
    updated = crud.add_scenarios_to_set(
        session=db,
        db_scenario_set=scenario_set,
        members=[ScenarioSetMemberEntry(scenario_id=scenario.id)],
    )
    assert updated.id == scenario_set.id
    scenarios, count = crud.list_scenarios_in_set(
        session=db, scenario_set_id=scenario_set.id
    )
    assert count == 1
    assert scenarios[0].scenario_id == scenario.id


def test_add_invalid_scenario_to_set(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    with pytest.raises(ValueError, match="Scenarios not found"):
        crud.add_scenarios_to_set(
            session=db,
            db_scenario_set=scenario_set,
            members=[ScenarioSetMemberEntry(scenario_id=uuid.uuid4())],
        )


def test_add_scenarios_duplicate_ids_in_request_rejected(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    scenario = create_test_scenario(db)
    with pytest.raises(ValueError, match="Duplicate scenario_id"):
        crud.add_scenarios_to_set(
            session=db,
            db_scenario_set=scenario_set,
            members=[
                ScenarioSetMemberEntry(scenario_id=scenario.id),
                ScenarioSetMemberEntry(scenario_id=scenario.id),
            ],
        )


def test_add_scenario_already_in_set_rejected(db: Session) -> None:
    scenario = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(scenario.id)
    )
    with pytest.raises(ValueError, match="Scenarios already in set"):
        crud.add_scenarios_to_set(
            session=db,
            db_scenario_set=scenario_set,
            members=[ScenarioSetMemberEntry(scenario_id=scenario.id)],
        )


def test_sum_member_repetitions_in_sets_batch(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    set_a = create_test_scenario_set(db, members=scenario_set_members(s1.id))
    set_b = create_test_scenario_set(db)
    crud.replace_scenarios_in_set(
        session=db,
        db_scenario_set=set_a,
        members=[
            ScenarioSetMemberEntry(scenario_id=s1.id, repetitions=2),
            ScenarioSetMemberEntry(scenario_id=s2.id, repetitions=3),
        ],
    )
    sums = crud.sum_member_repetitions_in_sets(
        session=db, scenario_set_ids=[set_a.id, set_b.id]
    )
    assert sums[set_a.id] == 5
    assert sums[set_b.id] == 0


def test_remove_scenario_from_set(db: Session) -> None:
    scenario = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(scenario.id)
    )

    updated = crud.remove_scenario_from_set(
        session=db,
        db_scenario_set=scenario_set,
        scenario_id=scenario.id,
    )
    assert updated.id == scenario_set.id
    _, count = crud.list_scenarios_in_set(session=db, scenario_set_id=scenario_set.id)
    assert count == 0


def test_replace_scenarios_in_set(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    s3 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(s1.id, s2.id)
    )

    updated = crud.replace_scenarios_in_set(
        session=db,
        db_scenario_set=scenario_set,
        members=[ScenarioSetMemberEntry(scenario_id=s3.id, repetitions=2)],
    )
    assert updated.id == scenario_set.id
    scenarios, count = crud.list_scenarios_in_set(
        session=db, scenario_set_id=scenario_set.id
    )
    assert count == 1
    assert scenarios[0].scenario_id == s3.id
    assert scenarios[0].repetitions == 2


def test_replace_with_invalid_scenario_ids(db: Session) -> None:
    s1 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, members=scenario_set_members(s1.id))
    with pytest.raises(ValueError, match="Scenarios not found"):
        crud.replace_scenarios_in_set(
            session=db,
            db_scenario_set=scenario_set,
            members=[ScenarioSetMemberEntry(scenario_id=uuid.uuid4())],
        )


def test_list_scenarios_in_set_ordered(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    s3 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(s3.id, s1.id, s2.id)
    )
    scenarios, count = crud.list_scenarios_in_set(
        session=db, scenario_set_id=scenario_set.id
    )
    assert count == 3
    assert scenarios[0].scenario_id == s3.id
    assert scenarios[1].scenario_id == s1.id
    assert scenarios[2].scenario_id == s2.id


def test_list_scenarios_in_set_paginated(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    s3 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(s1.id, s2.id, s3.id)
    )

    page1, count = crud.list_scenarios_in_set(
        session=db, scenario_set_id=scenario_set.id, skip=0, limit=2
    )
    assert count == 3
    assert len(page1) == 2
    assert page1[0].scenario_id == s1.id

    page2, _ = crud.list_scenarios_in_set(
        session=db, scenario_set_id=scenario_set.id, skip=2, limit=2
    )
    assert len(page2) == 1
    assert page2[0].scenario_id == s3.id


def test_version_increments_on_add(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    assert scenario_set.version == 1
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    updated = crud.add_scenarios_to_set(
        session=db,
        db_scenario_set=scenario_set,
        members=[
            ScenarioSetMemberEntry(scenario_id=s1.id),
            ScenarioSetMemberEntry(scenario_id=s2.id),
        ],
    )
    assert updated.version == 2


def test_version_increments_on_remove(db: Session) -> None:
    scenario = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(scenario.id)
    )
    assert scenario_set.version == 1
    updated = crud.remove_scenario_from_set(
        session=db, db_scenario_set=scenario_set, scenario_id=scenario.id
    )
    assert updated.version == 2


def test_version_not_incremented_on_noop_remove(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    assert scenario_set.version == 1
    updated = crud.remove_scenario_from_set(
        session=db, db_scenario_set=scenario_set, scenario_id=uuid.uuid4()
    )
    assert updated.version == 1


def test_version_increments_on_replace(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, members=scenario_set_members(s1.id))
    assert scenario_set.version == 1
    updated = crud.replace_scenarios_in_set(
        session=db,
        db_scenario_set=scenario_set,
        members=[ScenarioSetMemberEntry(scenario_id=s2.id)],
    )
    assert updated.version == 2


def test_version_increments_multiple_operations(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    s3 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db)
    assert scenario_set.version == 1

    crud.add_scenarios_to_set(
        session=db,
        db_scenario_set=scenario_set,
        members=[
            ScenarioSetMemberEntry(scenario_id=s1.id),
            ScenarioSetMemberEntry(scenario_id=s2.id),
        ],
    )
    crud.replace_scenarios_in_set(
        session=db,
        db_scenario_set=scenario_set,
        members=[ScenarioSetMemberEntry(scenario_id=s3.id)],
    )
    updated = crud.remove_scenario_from_set(
        session=db, db_scenario_set=scenario_set, scenario_id=s3.id
    )
    assert updated.version == 4


def test_version_not_bumped_on_metadata_update(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    assert scenario_set.version == 1
    updated = crud.update_scenario_set(
        session=db,
        db_scenario_set=scenario_set,
        scenario_set_in=ScenarioSetUpdate(name="Renamed", description="New desc"),
    )
    assert updated.version == 1


def test_delete_scenario_set(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    set_id = scenario_set.id
    crud.delete_scenario_set(session=db, db_scenario_set=scenario_set)
    fetched = crud.get_scenario_set(session=db, scenario_set_id=set_id)
    assert fetched is None


def test_get_scenarios_for_set_returns_active_only(db: Session) -> None:
    active = create_test_scenario(db, status="active")
    draft = create_test_scenario(db, status="draft")
    archived = create_test_scenario(db, status="archived")
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(active.id, draft.id, archived.id)
    )
    results = crud.get_scenarios_for_set(session=db, scenario_set_id=scenario_set.id)
    result_ids = [entry.scenario.id for entry in results]
    assert active.id in result_ids
    assert draft.id not in result_ids
    assert archived.id not in result_ids


def test_get_scenarios_for_set_preserves_order(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    s3 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(s3.id, s1.id, s2.id)
    )
    results = crud.get_scenarios_for_set(session=db, scenario_set_id=scenario_set.id)
    assert [e.scenario.id for e in results] == [s3.id, s1.id, s2.id]


def test_get_scenarios_for_set_includes_repetitions(db: Session) -> None:
    s1 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db)
    crud.replace_scenarios_in_set(
        session=db,
        db_scenario_set=scenario_set,
        members=[ScenarioSetMemberEntry(scenario_id=s1.id, repetitions=3)],
    )
    results = crud.get_scenarios_for_set(session=db, scenario_set_id=scenario_set.id)
    assert len(results) == 1
    assert results[0].repetitions == 3
    assert results[0].position == 0


def test_get_scenarios_for_set_empty(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    results = crud.get_scenarios_for_set(session=db, scenario_set_id=scenario_set.id)
    assert results == []


def test_sum_member_repetitions_in_set(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db)
    crud.replace_scenarios_in_set(
        session=db,
        db_scenario_set=scenario_set,
        members=[
            ScenarioSetMemberEntry(scenario_id=s1.id, repetitions=2),
            ScenarioSetMemberEntry(scenario_id=s2.id, repetitions=3),
        ],
    )
    total = crud.sum_member_repetitions_in_set(
        session=db, scenario_set_id=scenario_set.id
    )
    assert total == 5


def test_count_scenarios_in_sets_batch(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    set_a = create_test_scenario_set(db, members=scenario_set_members(s1.id, s2.id))
    set_b = create_test_scenario_set(db)

    counts = crud.count_scenarios_in_sets(
        session=db, scenario_set_ids=[set_a.id, set_b.id]
    )
    assert counts[set_a.id] == 2
    assert counts.get(set_b.id, 0) == 0
