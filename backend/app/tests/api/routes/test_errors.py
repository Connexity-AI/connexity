import uuid

from fastapi.testclient import TestClient

from app.core.config import settings


def test_404_consistent_format(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/test-cases/{uuid.uuid4()}",
        cookies=auth_cookies,
    )
    assert r.status_code == 404
    result = r.json()
    assert result["detail"] == "Test case not found"
    assert result["code"] == "NOT_FOUND"
    assert result["status"] == 404


def test_422_consistent_format(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/",
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
    r = client.get(f"{settings.API_V1_STR}/test-cases/")
    assert r.status_code == 401
    result = r.json()
    assert result["code"] == "UNAUTHORIZED"
    assert result["status"] == 401


def test_health_endpoint(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_mock_webhook_endpoint_returns_200(client: TestClient) -> None:
    r = client.post(
        "/mock-webhook",
        json={"event_type": "agent.deployed", "agent": {"id": "abc"}},
    )

    assert r.status_code == 200
    result = r.json()
    assert result["message"] == "Mock webhook received payload"
    assert result["received_event_type"] == "agent.deployed"
    assert result["payload_received"] is True
