import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.eval import (
    create_test_agent,
    create_test_run,
    create_test_scenario,
    create_test_scenario_result,
    create_test_scenario_set,
    scenario_set_members,
)


def _setup(db: Session) -> tuple:
    agent = create_test_agent(db)
    scenario = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(scenario.id)
    )
    run = create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    return run, scenario


def test_create_scenario_result(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, scenario = _setup(db)
    data = {
        "run_id": str(run.id),
        "scenario_id": str(scenario.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/scenario-results/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["run_id"] == str(run.id)
    assert result["scenario_id"] == str(scenario.id)


def test_list_scenario_results(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, scenario = _setup(db)
    create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    r = client.get(
        f"{settings.API_V1_STR}/scenario-results/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_list_scenario_results_filter_by_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, scenario = _setup(db)
    create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    r = client.get(
        f"{settings.API_V1_STR}/scenario-results/",
        params={"run_id": str(run.id)},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert all(item["run_id"] == str(run.id) for item in data["data"])


def test_get_scenario_result(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, scenario = _setup(db)
    result = create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    r = client.get(
        f"{settings.API_V1_STR}/scenario-results/{result.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(result.id)


def test_get_scenario_result_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/scenario-results/{uuid.uuid4()}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_update_scenario_result(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, scenario = _setup(db)
    result = create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    r = client.patch(
        f"{settings.API_V1_STR}/scenario-results/{result.id}",
        json={"passed": True, "turn_count": 3, "total_latency_ms": 500},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["passed"] is True
    assert updated["turn_count"] == 3
    assert updated["total_latency_ms"] == 500


def test_delete_scenario_result(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, scenario = _setup(db)
    result = create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    r = client.delete(
        f"{settings.API_V1_STR}/scenario-results/{result.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
