import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.eval import (
    create_test_scenario,
    create_test_scenario_set,
    scenario_set_members,
)


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
    assert result["version"] == 1


def test_create_scenario_set_with_scenarios(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    data = {
        "name": "Set With Scenarios",
        "members": [
            {"scenario_id": str(s1.id), "repetitions": 1},
            {"scenario_id": str(s2.id), "repetitions": 1},
        ],
    }
    r = client.post(
        f"{settings.API_V1_STR}/scenario-sets/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["scenario_count"] == 2
    assert result["version"] == 1

    # Verify scenarios are linked
    r2 = client.get(
        f"{settings.API_V1_STR}/scenario-sets/{result['id']}/scenarios",
        cookies=superuser_auth_cookies,
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["count"] == 2
    assert body["data"][0]["scenario_id"] == str(s1.id)
    assert body["data"][0]["repetitions"] == 1


def test_create_scenario_set_with_invalid_members(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    data = {
        "name": "Bad Set",
        "members": [{"scenario_id": str(uuid.uuid4()), "repetitions": 1}],
    }
    r = client.post(
        f"{settings.API_V1_STR}/scenario-sets/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_create_scenario_set_always_starts_at_version_1(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    data = {"name": "Fresh Set"}
    r = client.post(
        f"{settings.API_V1_STR}/scenario-sets/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 1


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
    result = r.json()
    assert result["name"] == "Patched Set"
    assert result["version"] == 1  # metadata change does NOT bump version


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
        json={"members": [{"scenario_id": str(s1.id), "repetitions": 1}]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["version"] == 2
    assert result["scenario_count"] == 1


def test_add_invalid_scenarios_to_set(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario_set = create_test_scenario_set(db)
    r = client.post(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios",
        json={"members": [{"scenario_id": str(uuid.uuid4()), "repetitions": 1}]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_replace_scenarios_in_set(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, members=scenario_set_members(s1.id))
    r = client.put(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios",
        json={"members": [{"scenario_id": str(s2.id), "repetitions": 1}]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["version"] == 2
    assert result["scenario_count"] == 1

    # Verify replacement
    r2 = client.get(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios",
        cookies=superuser_auth_cookies,
    )
    assert r2.json()["count"] == 1
    assert r2.json()["data"][0]["scenario_id"] == str(s2.id)


def test_replace_with_invalid_scenarios(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, members=scenario_set_members(s1.id))
    r = client.put(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios",
        json={"members": [{"scenario_id": str(uuid.uuid4()), "repetitions": 1}]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_remove_scenario_from_set(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, members=scenario_set_members(s1.id))
    r = client.delete(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios/{s1.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["version"] == 2
    assert result["scenario_count"] == 0


def test_scenario_count_in_response(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    data = {
        "name": "Count Check Set",
        "members": [
            {"scenario_id": str(s1.id), "repetitions": 1},
            {"scenario_id": str(s2.id), "repetitions": 1},
        ],
    }
    r = client.post(
        f"{settings.API_V1_STR}/scenario-sets/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["scenario_count"] == 2
    assert result["version"] == 1


def test_list_scenarios_in_set_paginated(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_scenario(db)
    s2 = create_test_scenario(db)
    s3 = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(s1.id, s2.id, s3.id)
    )

    r = client.get(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios",
        params={"skip": 0, "limit": 2},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 3
    assert len(data["data"]) == 2

    r2 = client.get(
        f"{settings.API_V1_STR}/scenario-sets/{scenario_set.id}/scenarios",
        params={"skip": 2, "limit": 2},
        cookies=superuser_auth_cookies,
    )
    assert r2.status_code == 200
    assert len(r2.json()["data"]) == 1
