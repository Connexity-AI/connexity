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
    assert "difficulty" in detail.lower()


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
    assert "name" in detail.lower()


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


# ── Export / Import ───────────────────────────────────────────────


def test_export_scenarios(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    create_test_scenario(db, tags=["export-test"])
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/export",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert "exported_at" in data
    assert data["count"] >= 1
    assert len(data["scenarios"]) == data["count"]
    assert (
        r.headers["content-disposition"]
        == 'attachment; filename="scenarios-export.json"'
    )


def test_export_scenarios_with_filters(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    tag = f"export-filter-{uuid.uuid4().hex[:6]}"
    create_test_scenario(db, tags=[tag], difficulty="hard")
    create_test_scenario(db, tags=["other-tag"], difficulty="normal")
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/export",
        params={"tag": tag},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert all(tag in s["tags"] for s in data["scenarios"])


def test_import_scenarios_create_new(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    payload = [
        {"name": "Import New 1", "tags": ["import-test"]},
        {"name": "Import New 2", "tags": ["import-test"]},
    ]
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/import",
        json=payload,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["created"] == 2
    assert result["skipped"] == 0
    assert result["overwritten"] == 0
    assert result["total"] == 2
    assert result["errors"] == []


def test_import_scenarios_round_trip(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    tag = f"roundtrip-{uuid.uuid4().hex[:6]}"
    create_test_scenario(
        db,
        name="Round Trip Scenario",
        tags=[tag],
        persona={"type": "tester", "description": "A tester", "instructions": "Test."},
        user_context={"key": "value"},
        expected_tool_calls=[{"tool": "test_tool", "expected_params": {"a": 1}}],
    )

    # Export
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/export",
        params={"tag": tag},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    exported = r.json()
    assert exported["count"] == 1
    original = exported["scenarios"][0]

    # Import with overwrite (same ids)
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/import",
        params={"on_conflict": "overwrite"},
        json=exported["scenarios"],
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["overwritten"] == 1

    # Fetch and compare
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/{original['id']}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    reimported = r.json()
    for field in (
        "name",
        "tags",
        "difficulty",
        "persona",
        "user_context",
        "expected_tool_calls",
    ):
        assert reimported[field] == original[field], f"Mismatch on {field}"


def test_import_scenarios_skip_conflict(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario = create_test_scenario(db, name="Original Name")
    payload = [
        {
            "id": str(scenario.id),
            "name": "Should Be Skipped",
            "tags": ["skip-test"],
        }
    ]
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/import",
        json=payload,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["skipped"] == 1
    assert result["created"] == 0

    # Verify original unchanged
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/{scenario.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.json()["name"] == "Original Name"


def test_import_scenarios_overwrite_conflict(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    scenario = create_test_scenario(
        db,
        name="Before Overwrite",
        persona={"type": "original", "description": "Keep me", "instructions": "Stay."},
        user_context={"preserved": True},
    )
    payload = [
        {
            "id": str(scenario.id),
            "name": "After Overwrite",
            "tags": ["overwrite-test"],
        }
    ]
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/import",
        params={"on_conflict": "overwrite"},
        json=payload,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["overwritten"] == 1
    assert result["errors"] == []

    # Verify updated field changed, unset fields preserved
    r = client.get(
        f"{settings.API_V1_STR}/scenarios/{scenario.id}",
        cookies=superuser_auth_cookies,
    )
    updated = r.json()
    assert updated["name"] == "After Overwrite"
    assert updated["persona"]["type"] == "original"
    assert updated["user_context"]["preserved"] is True


def test_import_scenarios_mixed(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    existing = create_test_scenario(db, name="Existing")
    payload = [
        {"id": str(existing.id), "name": "Skip Me"},
        {"name": "Brand New"},
    ]
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/import",
        json=payload,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["skipped"] == 1
    assert result["created"] == 1
    assert result["total"] == 2


def test_import_scenarios_empty_list(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/import",
        json=[],
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 400


def test_import_scenarios_unauthenticated(client: TestClient) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/scenarios/import",
        json=[{"name": "No Auth"}],
    )
    assert r.status_code in (401, 403)
