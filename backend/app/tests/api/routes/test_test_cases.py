import json
import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.services.llm import LLMResponse
from app.tests.utils.eval import (
    create_test_case_fixture,
    create_test_platform_agent,
)


def test_create_test_case(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    data = {
        "name": "Route TestCase",
        "tags": ["billing"],
        "difficulty": "hard",
    }
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["name"] == "Route TestCase"
    assert result["tags"] == ["billing"]
    assert result["difficulty"] == "hard"


def test_list_test_cases(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    create_test_case_fixture(db)
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_list_test_cases_filter_by_tag(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    tag = "route-tag-filter"
    create_test_case_fixture(db, tags=[tag])
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/",
        params={"tag": tag},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert all(tag in s["tags"] for s in data["data"])


def test_list_test_cases_filter_by_difficulty(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/",
        params={"difficulty": "hard"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_get_test_case(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    test_case = create_test_case_fixture(db)
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/{test_case.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(test_case.id)


def test_get_test_case_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/{uuid.uuid4()}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_update_test_case(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    test_case = create_test_case_fixture(db)
    r = client.patch(
        f"{settings.API_V1_STR}/test-cases/{test_case.id}",
        json={"name": "Patched TestCase"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Patched TestCase"


def test_delete_test_case(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    test_case = create_test_case_fixture(db)
    r = client.delete(
        f"{settings.API_V1_STR}/test-cases/{test_case.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_list_test_cases_search(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    create_test_case_fixture(db, name="Banana Split TestCase")
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/",
        params={"search": "banana split"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert any("Banana Split" in s["name"] for s in data["data"])


def test_list_test_cases_sort(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/",
        params={"sort_by": "name", "sort_order": "asc"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    names = [s["name"] for s in r.json()["data"]]
    assert names == sorted(names)


def test_list_test_cases_invalid_sort_order(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/",
        params={"sort_order": "invalid"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_create_test_case_invalid_difficulty(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/",
        json={"name": "Bad TestCase", "difficulty": "impossible"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "difficulty" in detail.lower()


def test_create_test_case_missing_name(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/",
        json={"tags": ["test"]},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "name" in detail.lower()


def test_create_test_case_with_persona_context_string(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/",
        json={"name": "Persona Context", "persona_context": "A polite customer"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["persona_context"] == "A polite customer"


def test_create_test_case_with_full_schema(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    data = {
        "name": "Full Schema Route Test",
        "persona_context": "A polite customer. Be cooperative.",
        "first_message": "Hello, I need help.",
        "user_context": {"order_id": "ORD-99999"},
        "expected_outcomes": ["Issue MUST be resolved"],
        "expected_tool_calls": [
            {"tool": "lookup_order", "expected_params": {"order_id": "ORD-99999"}},
        ],
    }
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["persona_context"] == "A polite customer. Be cooperative."
    assert result["user_context"]["order_id"] == "ORD-99999"
    assert result["expected_outcomes"] == ["Issue MUST be resolved"]
    assert result["expected_tool_calls"][0]["tool"] == "lookup_order"


def test_update_test_case_with_new_fields(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    test_case = create_test_case_fixture(db)
    r = client.patch(
        f"{settings.API_V1_STR}/test-cases/{test_case.id}",
        json={
            "persona_context": "An angry customer. Express frustration.",
            "expected_outcomes": ["Call MUST be escalated"],
        },
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["persona_context"] == "An angry customer. Express frustration."
    assert result["expected_outcomes"] == ["Call MUST be escalated"]


# ── Export / Import ───────────────────────────────────────────────


def test_export_test_cases(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    create_test_case_fixture(db, tags=["export-test"])
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/export",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert "exported_at" in data
    assert data["count"] >= 1
    assert len(data["test_cases"]) == data["count"]
    assert (
        r.headers["content-disposition"]
        == 'attachment; filename="test-cases-export.json"'
    )


def test_export_test_cases_with_filters(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    tag = f"export-filter-{uuid.uuid4().hex[:6]}"
    create_test_case_fixture(db, tags=[tag], difficulty="hard")
    create_test_case_fixture(db, tags=["other-tag"], difficulty="normal")
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/export",
        params={"tag": tag},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert all(tag in s["tags"] for s in data["test_cases"])


def test_import_test_cases_create_new(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    payload = [
        {"name": "Import New 1", "tags": ["import-test"]},
        {"name": "Import New 2", "tags": ["import-test"]},
    ]
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/import",
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


def test_import_test_cases_round_trip(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    tag = f"roundtrip-{uuid.uuid4().hex[:6]}"
    create_test_case_fixture(
        db,
        name="Round Trip TestCase",
        tags=[tag],
        persona_context="A tester. Test.",
        user_context={"key": "value"},
        expected_tool_calls=[{"tool": "test_tool", "expected_params": {"a": 1}}],
    )

    # Export
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/export",
        params={"tag": tag},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    exported = r.json()
    assert exported["count"] == 1
    original = exported["test_cases"][0]

    # Import with overwrite (same ids)
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/import",
        params={"on_conflict": "overwrite"},
        json=exported["test_cases"],
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["overwritten"] == 1

    # Fetch and compare
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/{original['id']}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    reimported = r.json()
    for field in (
        "name",
        "tags",
        "difficulty",
        "persona_context",
        "user_context",
        "expected_tool_calls",
    ):
        assert reimported[field] == original[field], f"Mismatch on {field}"


def test_import_test_cases_skip_conflict(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    test_case = create_test_case_fixture(db, name="Original Name")
    payload = [
        {
            "id": str(test_case.id),
            "name": "Should Be Skipped",
            "tags": ["skip-test"],
        }
    ]
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/import",
        json=payload,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["skipped"] == 1
    assert result["created"] == 0

    # Verify original unchanged
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/{test_case.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.json()["name"] == "Original Name"


def test_import_test_cases_overwrite_conflict(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    test_case = create_test_case_fixture(
        db,
        name="Before Overwrite",
        persona_context="Original persona. Keep me. Stay.",
        user_context={"preserved": True},
    )
    payload = [
        {
            "id": str(test_case.id),
            "name": "After Overwrite",
            "tags": ["overwrite-test"],
        }
    ]
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/import",
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
        f"{settings.API_V1_STR}/test-cases/{test_case.id}",
        cookies=superuser_auth_cookies,
    )
    updated = r.json()
    assert updated["name"] == "After Overwrite"
    assert "Original persona" in updated["persona_context"]
    assert updated["user_context"]["preserved"] is True


def test_import_test_cases_mixed(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    existing = create_test_case_fixture(db, name="Existing")
    payload = [
        {"id": str(existing.id), "name": "Skip Me"},
        {"name": "Brand New"},
    ]
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/import",
        json=payload,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["skipped"] == 1
    assert result["created"] == 1
    assert result["total"] == 2


def test_import_test_cases_empty_list(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/import",
        json=[],
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 400


def test_import_test_cases_unauthenticated(client: TestClient) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/import",
        json=[{"name": "No Auth"}],
    )
    assert r.status_code in (401, 403)


def test_test_case_ai_from_transcript_missing_transcript(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/ai",
        json={
            "mode": "from_transcript",
            "user_message": "convert",
            "agent_id": str(agent.id),
        },
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_test_case_ai_edit_missing_test_case_id(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/ai",
        json={
            "mode": "edit",
            "user_message": "fix",
            "agent_id": str(agent.id),
        },
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_test_case_ai_edit_agent_mismatch(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    a1 = create_test_platform_agent(db)
    a2 = create_test_platform_agent(db)
    tc = create_test_case_fixture(db, agent_id=a1.id)
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/ai",
        json={
            "mode": "edit",
            "user_message": "x",
            "agent_id": str(a2.id),
            "test_case_id": str(tc.id),
        },
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422
    assert "belong" in r.json()["detail"].lower()


def test_test_case_ai_create_preview(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    mock_resp = LLMResponse(
        content="",
        model="gpt-4o",
        usage={},
        latency_ms=1,
        tool_calls=[
            {
                "id": "c1",
                "type": "function",
                "function": {
                    "name": "create_test_case",
                    "arguments": json.dumps(
                        {
                            "name": "AI Case",
                            "tags": ["normal"],
                            "difficulty": "normal",
                            "persona_context": "p",
                            "first_message": "hi",
                        }
                    ),
                },
            }
        ],
    )
    with patch(
        "app.services.test_case_generator.agent.core.call_llm",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/ai",
            json={
                "mode": "create",
                "user_message": "one case",
                "agent_id": str(agent.id),
                "persist": False,
            },
            cookies=superuser_auth_cookies,
        )
    assert r.status_code == 200
    data = r.json()
    assert len(data["created"]) == 1
    assert data["created"][0]["name"] == "AI Case"
    assert data["edited"] is None


def test_test_case_ai_edit_preview_default_no_db_write(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    tc = create_test_case_fixture(db, agent_id=agent.id, name="Original Name")
    mock_resp = LLMResponse(
        content="",
        model="gpt-4o",
        usage={},
        latency_ms=1,
        tool_calls=[
            {
                "id": "c1",
                "type": "function",
                "function": {
                    "name": "edit_test_case",
                    "arguments": json.dumps(
                        {
                            "name": "Renamed By AI",
                            "tags": ["edge-case"],
                            "difficulty": "hard",
                            "persona_context": "pc",
                            "first_message": "yo",
                        }
                    ),
                },
            }
        ],
    )
    with patch(
        "app.services.test_case_generator.agent.core.call_llm",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/ai",
            json={
                "mode": "edit",
                "user_message": "rename",
                "agent_id": str(agent.id),
                "test_case_id": str(tc.id),
            },
            cookies=superuser_auth_cookies,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["edited"]["name"] == "Renamed By AI"
    db.refresh(tc)
    assert tc.name == "Original Name"


def test_test_case_ai_edit_persist_updates_db(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    tc = create_test_case_fixture(db, agent_id=agent.id, name="Before Persist")
    mock_resp = LLMResponse(
        content="",
        model="gpt-4o",
        usage={},
        latency_ms=1,
        tool_calls=[
            {
                "id": "c1",
                "type": "function",
                "function": {
                    "name": "edit_test_case",
                    "arguments": json.dumps(
                        {
                            "name": "After Persist",
                            "tags": ["normal"],
                            "difficulty": "normal",
                            "persona_context": "pc",
                            "first_message": "m",
                        }
                    ),
                },
            }
        ],
    )
    with patch(
        "app.services.test_case_generator.agent.core.call_llm",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/ai",
            json={
                "mode": "edit",
                "user_message": "update",
                "agent_id": str(agent.id),
                "test_case_id": str(tc.id),
                "persist": True,
            },
            cookies=superuser_auth_cookies,
        )
    assert r.status_code == 200
    db.refresh(tc)
    assert tc.name == "After Persist"
