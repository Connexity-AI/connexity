import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import CustomMetricCreate, MetricTier, ScoreType
from app.services.metric_generator import MetricGenerateResult
from app.tests.utils.user import create_random_user


def _create_body(*, name: str) -> dict[str, object]:
    return {
        "name": name,
        "display_name": "API Metric",
        "description": "Test metric via API.",
        "tier": MetricTier.KNOWLEDGE.value,
        "default_weight": 0.25,
        "score_type": ScoreType.SCORED.value,
        "rubric": (
            "Measures: knowledge grounding.\n\n"
            "5: Fully grounded.\n   Example: Agent cited policy text."
        ),
        "include_in_defaults": False,
    }


def test_custom_metrics_require_auth(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/custom-metrics/")
    assert r.status_code == 401


def test_create_list_get_update_delete_custom_metric(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    name = f"api_metric_{uuid.uuid4().hex[:10]}"
    create_r = client.post(
        f"{settings.API_V1_STR}/custom-metrics/",
        json=_create_body(name=name),
        cookies=superuser_auth_cookies,
    )
    assert create_r.status_code == 200
    created = create_r.json()
    assert created["name"] == name
    metric_id = created["id"]

    list_r = client.get(
        f"{settings.API_V1_STR}/custom-metrics/",
        cookies=superuser_auth_cookies,
    )
    assert list_r.status_code == 200
    listed_names = {m["name"] for m in list_r.json()["data"]}
    assert name in listed_names

    get_r = client.get(
        f"{settings.API_V1_STR}/custom-metrics/{metric_id}",
        cookies=superuser_auth_cookies,
    )
    assert get_r.status_code == 200
    assert get_r.json()["display_name"] == "API Metric"

    patch_r = client.put(
        f"{settings.API_V1_STR}/custom-metrics/{metric_id}",
        json={"display_name": "Updated"},
        cookies=superuser_auth_cookies,
    )
    assert patch_r.status_code == 200
    assert patch_r.json()["display_name"] == "Updated"

    del_r = client.delete(
        f"{settings.API_V1_STR}/custom-metrics/{metric_id}",
        cookies=superuser_auth_cookies,
    )
    assert del_r.status_code == 200

    get_again = client.get(
        f"{settings.API_V1_STR}/custom-metrics/{metric_id}",
        cookies=superuser_auth_cookies,
    )
    assert get_again.status_code == 404


def test_create_custom_metric_reserved_builtin_name_conflict(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    body = _create_body(name="tool_routing")
    r = client.post(
        f"{settings.API_V1_STR}/custom-metrics/",
        json=body,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 409
    assert "built-in" in r.json()["detail"].lower()


def test_create_duplicate_name_same_user(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    name = f"dup_{uuid.uuid4().hex[:10]}"
    body = _create_body(name=name)
    assert (
        client.post(
            f"{settings.API_V1_STR}/custom-metrics/",
            json=body,
            cookies=superuser_auth_cookies,
        ).status_code
        == 200
    )
    r2 = client.post(
        f"{settings.API_V1_STR}/custom-metrics/",
        json=body,
        cookies=superuser_auth_cookies,
    )
    assert r2.status_code == 409


def test_custom_metric_other_owner_get_returns_404(
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    normal_user_auth_cookies: dict[str, str],
) -> None:
    name = f"isolated_{uuid.uuid4().hex[:10]}"
    create_r = client.post(
        f"{settings.API_V1_STR}/custom-metrics/",
        json=_create_body(name=name),
        cookies=superuser_auth_cookies,
    )
    assert create_r.status_code == 200
    metric_id = create_r.json()["id"]

    other_get = client.get(
        f"{settings.API_V1_STR}/custom-metrics/{metric_id}",
        cookies=normal_user_auth_cookies,
    )
    assert other_get.status_code == 404

    other_put = client.put(
        f"{settings.API_V1_STR}/custom-metrics/{metric_id}",
        json={"display_name": "Hijack"},
        cookies=normal_user_auth_cookies,
    )
    assert other_put.status_code == 404

    other_del = client.delete(
        f"{settings.API_V1_STR}/custom-metrics/{metric_id}",
        cookies=normal_user_auth_cookies,
    )
    assert other_del.status_code == 404


def test_list_custom_metrics_does_not_include_other_users(
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    other = create_random_user(db)
    name_other = f"other_user_{uuid.uuid4().hex[:10]}"
    crud.create_custom_metric(
        session=db,
        metric_in=CustomMetricCreate(
            name=name_other,
            display_name="Other",
            description="d",
            tier=MetricTier.DELIVERY,
            default_weight=0.1,
            score_type=ScoreType.BINARY,
            rubric="Measures: x.\n\nPass: ok\nExample: a\nFail: no\nExample: b",
            include_in_defaults=False,
        ),
        owner_id=other.id,
    )

    r = client.get(
        f"{settings.API_V1_STR}/custom-metrics/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    names = {m["name"] for m in r.json()["data"]}
    assert name_other not in names


def test_create_custom_metric_invalid_slug(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    body = _create_body(name="Bad-Name")
    r = client.post(
        f"{settings.API_V1_STR}/custom-metrics/",
        json=body,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_generate_custom_metric_preview_mocked_llm(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    rubric = (
        "Measures: whether the agent closed the loop.\n\n"
        "Pass: User goal addressed.\nExample: Agent confirmed reservation.\n"
        "Fail: Left hanging.\nExample: Agent stopped mid-flow."
    )
    with patch(
        "app.api.routes.custom_metrics.generate_metric",
        new_callable=AsyncMock,
        return_value=MetricGenerateResult(
            name="llm_metric",
            display_name="Llm Metric",
            description="Whether the agent closed the loop.",
            tier=MetricTier.PROCESS,
            default_weight=0.15,
            score_type=ScoreType.BINARY,
            rubric=rubric,
            model_used="mock",
            generation_time_ms=10,
        ),
    ):
        r = client.post(
            f"{settings.API_V1_STR}/custom-metrics/generate",
            json={"description": "Close the user loop"},
            cookies=superuser_auth_cookies,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "llm_metric"
    assert data["score_type"] == ScoreType.BINARY.value
