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
