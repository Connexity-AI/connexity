from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.services.test_case_generator.conftest import MOCK_LLM_RESPONSE
from app.tests.utils.eval import create_test_agent


async def _mock_generate(request):  # type: ignore[no-untyped-def]
    """Return pre-built TestCaseCreate objects from mock data."""
    from app.services.test_case_generator.core import _parse_test_cases

    test_cases = _parse_test_cases(MOCK_LLM_RESPONSE, expected_count=request.count)
    return test_cases, "gpt-4o", 1500


def test_generate_test_cases_endpoint_success(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_generate,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={"agent_prompt": "You are a helpful agent.", "count": 10},
            cookies=superuser_auth_cookies,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 10
    assert data["model_used"] == "gpt-4o"
    assert data["generation_time_ms"] == 1500
    assert len(data["test_cases"]) == 10


def test_generate_test_cases_persists_drafts(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_generate,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={"agent_prompt": "You are a helpful agent.", "persist": True},
            cookies=superuser_auth_cookies,
        )
    assert r.status_code == 200
    data = r.json()
    for tc in data["test_cases"]:
        assert tc["status"] == "draft"
        assert tc["id"] is not None


def test_generate_test_cases_with_agent_id(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_generate,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={
                "agent_prompt": "You are a helpful agent.",
                "persist": True,
                "agent_id": str(agent.id),
            },
            cookies=superuser_auth_cookies,
        )
    assert r.status_code == 200
    for tc in r.json()["test_cases"]:
        assert tc["agent_id"] == str(agent.id)


def test_generate_test_cases_no_persist(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_generate,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={
                "agent_prompt": "You are a helpful agent.",
                "persist": False,
            },
            cookies=superuser_auth_cookies,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 10


def test_generate_test_cases_unauthenticated(client: TestClient) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/generate",
        json={"agent_prompt": "You are a helpful agent."},
    )
    assert r.status_code in (401, 403)


def test_generate_test_cases_llm_error(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={"agent_prompt": "You are a helpful agent."},
            cookies=superuser_auth_cookies,
        )
    assert r.status_code == 502


def test_generate_test_cases_invalid_request(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/generate",
        json={},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422
