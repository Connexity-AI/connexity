from sqlmodel import Session

from app import crud
from app.models import ScenarioSetUpdate
from app.tests.utils.eval import (
    create_test_scenario,
    create_test_scenario_set,
)


def test_create_scenario_set(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    assert scenario_set.id is not None
    assert scenario_set.name.startswith("test-set-")


def test_create_scenario_set_with_scenarios(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, scenario_ids=[s1.id, s2.id])
    scenarios = crud.list_scenarios_in_set(session=db, scenario_set_id=scenario_set.id)
    assert len(scenarios) == 2
    assert scenarios[0].id == s1.id
    assert scenarios[1].id == s2.id


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


def test_add_scenario_to_set(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    scenario = create_test_scenario(db)
    member = crud.add_scenario_to_set(
        session=db,
        scenario_set_id=scenario_set.id,
        scenario_id=scenario.id,
        position=0,
    )
    assert member.scenario_set_id == scenario_set.id
    assert member.scenario_id == scenario.id


def test_remove_scenario_from_set(db: Session) -> None:
    scenario = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, scenario_ids=[scenario.id])

    crud.remove_scenario_from_set(
        session=db,
        scenario_set_id=scenario_set.id,
        scenario_id=scenario.id,
    )
    scenarios = crud.list_scenarios_in_set(session=db, scenario_set_id=scenario_set.id)
    assert len(scenarios) == 0


def test_replace_scenarios_in_set(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    s3 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, scenario_ids=[s1.id, s2.id])

    crud.replace_scenarios_in_set(
        session=db,
        scenario_set_id=scenario_set.id,
        scenario_ids=[s3.id],
    )
    scenarios = crud.list_scenarios_in_set(session=db, scenario_set_id=scenario_set.id)
    assert len(scenarios) == 1
    assert scenarios[0].id == s3.id


def test_list_scenarios_in_set_ordered(db: Session) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    s3 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, scenario_ids=[s3.id, s1.id, s2.id])
    scenarios = crud.list_scenarios_in_set(session=db, scenario_set_id=scenario_set.id)
    assert scenarios[0].id == s3.id
    assert scenarios[1].id == s1.id
    assert scenarios[2].id == s2.id


def test_delete_scenario_set(db: Session) -> None:
    scenario_set = create_test_scenario_set(db)
    set_id = scenario_set.id
    crud.delete_scenario_set(session=db, db_scenario_set=scenario_set)
    fetched = crud.get_scenario_set(session=db, scenario_set_id=set_id)
    assert fetched is None
