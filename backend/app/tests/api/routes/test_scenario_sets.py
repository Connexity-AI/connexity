import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.eval import create_test_scenario, create_test_scenario_set


def test_create_scenario_set(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    data = {"name": "Route Set", "description": "Test set"}
    r = client.post(
        f"{settings.API_V1_STR}/scenario-sets/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["name"] == "Route Set"


def test_create_scenario_set_with_scenarios(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    data = {
        "name": "Set With Scenarios",
        "scenario_ids": [str(s1.id), str(s2.id)],
    }
    r = client.post(
        f"{settings.API_V1_STR}/scenario-sets/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    set_id = r.json()["id"]

    # Verify scenarios are linked
    r2 = client.get(
        f"{settings.API_V1_STR}/scenario-sets/{set_id}/scenarios",
        cookies=superuser_auth_cookies,
    )
    assert r2.status_code == 200
    assert r2.json()["count"] == 2


def test_list_scenario_sets(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    create_test_scenario_set(db)
    r = client.get(
        f"{settings.API_V1_STR}/scenario-sets/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_get_scenario_set(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario_set = create_test_scenario_set(db)
    r = client.get(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(scenario_set.id)


def test_get_scenario_set_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/scenario-sets/{uuid.uuid4()}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_update_scenario_set(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario_set = create_test_scenario_set(db)
    r = client.patch(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}",
        json={"name": "Patched Set"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Patched Set"


def test_delete_scenario_set(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario_set = create_test_scenario_set(db)
    r = client.delete(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_add_scenarios_to_set(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario_set = create_test_scenario_set(db)
    s1 = create_test_scenario(db)
    r = client.post(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios",
        json={"scenario_ids": [str(s1.id)]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_replace_scenarios_in_set(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, scenario_ids=[s1.id])
    r = client.put(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios",
        json={"scenario_ids": [str(s2.id)]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200

    # Verify replacement
    r2 = client.get(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios",
        cookies=superuser_auth_cookies,
    )
    assert r2.json()["count"] == 1
    assert r2.json()["data"][0]["id"] == str(s2.id)


def test_remove_scenario_from_set(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, scenario_ids=[s1.id])
    r = client.delete(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios/{s1.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
