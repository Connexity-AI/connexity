import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


def test_404_consistent_format(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/agents/{uuid.uuid4()}/page",
        cookies=auth_cookies,
    )
    assert r.status_code == 404
    result = r.json()
    assert result["detail"] == "Agent not found"
    assert result["code"] == "NOT_FOUND"
    assert result["status"] == 404


def test_422_consistent_format(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/workspaces/",
        json={},
        cookies=auth_cookies,
    )
    assert r.status_code == 422
    result = r.json()
    assert "code" in result
    assert result["code"] == "VALIDATION_ERROR"
    assert result["status"] == 422
    assert "detail" in result


def test_401_consistent_format(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/agents/list")
    assert r.status_code == 401
    result = r.json()
    assert result["code"] == "UNAUTHORIZED"
    assert result["status"] == 401


def test_health_endpoint(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


@pytest.mark.parametrize(
    "path",
    [
        "/agents/",
        "/runs/",
        "/eval-configs/",
        "/test-cases/",
        "/test-case-results/",
        "/custom-metrics/",
        "/environments/",
        "/config/available-metrics",
    ],
)
def test_routes_of_the_old_eval_stack_are_gone(
    client: TestClient, auth_cookies: dict[str, str], path: str
) -> None:
    r = client.get(f"{settings.API_V1_STR}{path}", cookies=auth_cookies)
    assert r.status_code == 404
