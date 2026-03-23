import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.eval import (
    create_test_agent,
    create_test_run,
    create_test_scenario,
    create_test_scenario_set,
)


def _setup(db: Session) -> tuple:
    agent = create_test_agent(db)
    scenario = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, scenario_ids=[scenario.id])
    return agent, scenario_set


def test_create_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, scenario_set = _setup(db)
    data = {
        "agent_id": str(agent.id),
        "agent_endpoint_url": "http://localhost:8080/agent",
        "scenario_set_id": str(scenario_set.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/runs/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["agent_id"] == str(agent.id)
    assert result["status"] == "pending"


def test_list_runs(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, scenario_set = _setup(db)
    create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    r = client.get(
        f"{settings.API_V1_STR}/runs/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_list_runs_filter_by_agent(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, scenario_set = _setup(db)
    create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    r = client.get(
        f"{settings.API_V1_STR}/runs/",
        params={"agent_id": str(agent.id)},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert all(item["agent_id"] == str(agent.id) for item in data["data"])


def test_list_runs_filter_by_status(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/runs/",
        params={"status": "pending"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_get_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, scenario_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    r = client.get(
        f"{settings.API_V1_STR}/runs/{run.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(run.id)


def test_get_run_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/runs/{uuid.uuid4()}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_update_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, scenario_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    r = client.patch(
        f"{settings.API_V1_STR}/runs/{run.id}",
        json={"status": "running"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "running"


def test_delete_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, scenario_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    r = client.delete(
        f"{settings.API_V1_STR}/runs/{run.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
