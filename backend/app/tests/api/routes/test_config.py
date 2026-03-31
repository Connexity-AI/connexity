import uuid

from fastapi.testclient import TestClient

from app.core.config import settings


def test_get_config(client: TestClient, superuser_auth_cookies: dict[str, str]) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/config/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["project_name"] == settings.PROJECT_NAME
    assert result["api_version"] == settings.API_V1_STR
    assert result["environment"] in ("local", "staging", "production")
    assert result["docs_url"] == "/docs"


def test_get_config_requires_auth(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/config/")
    assert r.status_code == 401


def test_available_metrics_includes_custom_metrics(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    before = client.get(
        f"{settings.API_V1_STR}/config/available-metrics",
        cookies=superuser_auth_cookies,
    )
    assert before.status_code == 200
    count_before = before.json()["count"]

    name = f"avail_{uuid.uuid4().hex[:10]}"
    create_r = client.post(
        f"{settings.API_V1_STR}/custom-metrics/",
        json={
            "name": name,
            "display_name": "Avail Test",
            "description": "Listed in config.",
            "tier": "execution",
            "default_weight": 0.1,
            "score_type": "scored",
            "rubric": "Measures: test.\n5: ok.\n   Example: Agent replied.",
            "include_in_defaults": False,
        },
        cookies=superuser_auth_cookies,
    )
    assert create_r.status_code == 200

    after = client.get(
        f"{settings.API_V1_STR}/config/available-metrics",
        cookies=superuser_auth_cookies,
    )
    assert after.status_code == 200
    payload = after.json()
    assert payload["count"] == count_before + 1
    metric_names = {m["name"] for m in payload["data"]}
    assert name in metric_names
    assert "tool_routing" in metric_names
