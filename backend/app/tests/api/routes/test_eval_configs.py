import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_eval_config,
    eval_config_members,
)


def test_create_eval_config(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    data = {
        "name": "Route Config",
        "description": "Test config",
        "agent_id": str(agent.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["name"] == "Route Config"
    assert result["version"] == 1


def test_create_eval_config_with_test_cases(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    data = {
        "name": "Config With TestCases",
        "agent_id": str(agent.id),
        "members": [
            {"test_case_id": str(s1.id), "repetitions": 1},
            {"test_case_id": str(s2.id), "repetitions": 1},
        ],
    }
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["test_case_count"] == 2
    assert result["version"] == 1

    # Verify test cases are linked
    r2 = client.get(
        f"{settings.API_V1_STR}/eval-configs/{result['id']}/test-cases",
        cookies=superuser_auth_cookies,
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["count"] == 2
    assert body["data"][0]["test_case_id"] == str(s1.id)
    assert body["data"][0]["repetitions"] == 1


def test_create_eval_config_with_invalid_members(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    data = {
        "name": "Bad Config",
        "agent_id": str(agent.id),
        "members": [{"test_case_id": str(uuid.uuid4()), "repetitions": 1}],
    }
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_create_eval_config_always_starts_at_version_1(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    data = {"name": "Fresh Config", "agent_id": str(agent.id)}
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 1


def test_list_eval_configs(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    create_test_eval_config(db)
    r = client.get(
        f"{settings.API_V1_STR}/eval-configs/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_get_eval_config(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    eval_config = create_test_eval_config(db)
    r = client.get(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(eval_config.id)


def test_get_eval_config_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/eval-configs/{uuid.uuid4()}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_update_eval_config(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    eval_config = create_test_eval_config(db)
    r = client.patch(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}",
        json={"name": "Patched Config"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["name"] == "Patched Config"
    assert result["version"] == 1  # metadata change does NOT bump version


def test_delete_eval_config(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    eval_config = create_test_eval_config(db)
    r = client.delete(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_add_test_cases_to_config(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    eval_config = create_test_eval_config(db)
    s1 = create_test_case_fixture(db)
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}/test-cases",
        json={"members": [{"test_case_id": str(s1.id), "repetitions": 1}]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["version"] == 2
    assert result["test_case_count"] == 1


def test_add_invalid_test_cases_to_config(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    eval_config = create_test_eval_config(db)
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}/test-cases",
        json={"members": [{"test_case_id": str(uuid.uuid4()), "repetitions": 1}]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_replace_test_cases_in_config(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(s1.id))
    r = client.put(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}/test-cases",
        json={"members": [{"test_case_id": str(s2.id), "repetitions": 1}]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["version"] == 2
    assert result["test_case_count"] == 1

    # Verify replacement
    r2 = client.get(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}/test-cases",
        cookies=superuser_auth_cookies,
    )
    assert r2.json()["count"] == 1
    assert r2.json()["data"][0]["test_case_id"] == str(s2.id)


def test_replace_with_invalid_test_cases(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(s1.id))
    r = client.put(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}/test-cases",
        json={"members": [{"test_case_id": str(uuid.uuid4()), "repetitions": 1}]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_remove_test_case_from_config(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(s1.id))
    r = client.delete(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}/test-cases/{s1.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["version"] == 2
    assert result["test_case_count"] == 0


def test_test_case_count_in_response(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    data = {
        "name": "Count Check Config",
        "agent_id": str(agent.id),
        "members": [
            {"test_case_id": str(s1.id), "repetitions": 1},
            {"test_case_id": str(s2.id), "repetitions": 1},
        ],
    }
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["test_case_count"] == 2
    assert result["version"] == 1


def test_list_test_cases_in_config_paginated(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    s1 = create_test_case_fixture(db)
    s2 = create_test_case_fixture(db)
    s3 = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, members=eval_config_members(s1.id, s2.id, s3.id)
    )

    r = client.get(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}/test-cases",
        params={"skip": 0, "limit": 2},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 3
    assert len(data["data"]) == 2

    r2 = client.get(
        f"{settings.API_V1_STR}/eval-configs/{eval_config.id}/test-cases",
        params={"skip": 2, "limit": 2},
        cookies=superuser_auth_cookies,
    )
    assert r2.status_code == 200
    assert len(r2.json()["data"]) == 1
