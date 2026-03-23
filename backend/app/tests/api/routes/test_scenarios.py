import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.eval import create_test_scenario


def test_create_scenario(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    data = {
        "name": "Route Scenario",
        "tags": ["billing"],
        "difficulty": "hard",
    }
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["name"] == "Route Scenario"
    assert result["tags"] == ["billing"]
    assert result["difficulty"] == "hard"


def test_list_scenarios(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    create_test_scenario(db)
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_list_scenarios_filter_by_tag(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    tag = "route-tag-filter"
    create_test_scenario(db, tags=[tag])
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/",
        params={"tag": tag},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert all(tag in s["tags"] for s in data["data"])


def test_list_scenarios_filter_by_difficulty(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/",
        params={"difficulty": "hard"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_get_scenario(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario = create_test_scenario(db)
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/{scenario.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(scenario.id)


def test_get_scenario_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/{uuid.uuid4()}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_update_scenario(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario = create_test_scenario(db)
    r = client.patch(
        f"{settings.API_V1_STR}/scenarios/{scenario.id}",
        json={"name": "Patched Scenario"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Patched Scenario"


def test_delete_scenario(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario = create_test_scenario(db)
    r = client.delete(
        f"{settings.API_V1_STR}/scenarios/{scenario.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_list_scenarios_search(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    create_test_scenario(db, name="Banana Split Scenario")
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/",
        params={"search": "banana split"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert any("Banana Split" in s["name"] for s in data["data"])


def test_list_scenarios_sort(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/",
        params={"sort_by": "name", "sort_order": "asc"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    names = [s["name"] for s in r.json()["data"]]
    assert names == sorted(names)


def test_list_scenarios_invalid_sort_order(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/",
        params={"sort_order": "invalid"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_create_scenario_invalid_difficulty(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/",
        json={"name": "Bad Scenario", "difficulty": "impossible"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert any("difficulty" in str(e).lower() for e in detail)


def test_create_scenario_missing_name(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/",
        json={"tags": ["test"]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert any("name" in str(e).lower() for e in detail)


def test_create_scenario_invalid_persona_structure(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/",
        json={"name": "Bad Persona", "persona": {"wrong_field": "value"}},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_create_scenario_with_full_schema(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    data = {
        "name": "Full Schema Route Test",
        "persona": {
            "type": "polite-customer",
            "description": "A polite customer",
            "instructions": "Be cooperative.",
        },
        "initial_message": "Hello, I need help.",
        "user_context": {"order_id": "ORD-99999"},
        "max_turns": 10,
        "expected_outcomes": {"issue_resolved": True},
        "expected_tool_calls": [
            {"tool": "lookup_order", "expected_params": {"order_id": "ORD-99999"}},
        ],
    }
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["persona"]["type"] == "polite-customer"
    assert result["user_context"]["order_id"] == "ORD-99999"
    assert result["expected_outcomes"]["issue_resolved"] is True
    assert result["expected_tool_calls"][0]["tool"] == "lookup_order"
    assert result["max_turns"] == 10


def test_update_scenario_with_new_fields(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario = create_test_scenario(db)
    r = client.patch(
        f"{settings.API_V1_STR}/scenarios/{scenario.id}",
        json={
            "persona": {
                "type": "angry-customer",
                "description": "An angry customer",
                "instructions": "Express frustration.",
            },
            "expected_outcomes": {"escalated": True},
        },
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["persona"]["type"] == "angry-customer"
    assert result["expected_outcomes"]["escalated"] is True
