import uuid

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.api.routes import config as config_route
from app.core.config import settings
from app.services.llm_models import (
    LLMModelProviderPublic,
    LLMModelPublic,
    LLMModelsPublic,
)


def test_get_config(client: TestClient, auth_cookies: dict[str, str]) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/config/",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["project_name"] == settings.PROJECT_NAME
    assert result["api_version"] == settings.API_V1_STR
    assert result["environment"] in ("local", "staging", "production")
    assert result["docs_url"] == "/docs"
    assert result["default_llm_model"] == settings.default_llm_id


def test_get_config_requires_auth(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/config/")
    assert r.status_code == 401


def test_llm_models_requires_auth(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/config/llm-models")
    assert r.status_code == 401


def test_predefined_tools_requires_auth(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/config/predefined-tools")
    assert r.status_code == 401


def test_predefined_tools_returns_end_and_transfer(
    client: TestClient,
    auth_cookies: dict[str, str],
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/config/predefined-tools",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["count"] == 2
    names = {row["function"]["name"] for row in payload["data"]}
    assert names == {"end_call", "transfer_call"}
    end = next(r for r in payload["data"] if r["function"]["name"] == "end_call")
    assert end["platform_config"]["terminating"] is True
    assert end["platform_config"]["predefined"] is True
    xfer = next(r for r in payload["data"] if r["function"]["name"] == "transfer_call")
    req = xfer["function"]["parameters"]["required"]
    assert req == ["to_phone_number"]


def test_llm_models_returns_catalog(
    client: TestClient,
    auth_cookies: dict[str, str],
    monkeypatch: MonkeyPatch,
) -> None:
    catalog = LLMModelsPublic(
        default_model="openai/gpt-4o-mini",
        count=1,
        data=[
            LLMModelProviderPublic(
                provider="openai",
                label="OpenAI",
                default_model="openai/gpt-4o-mini",
                models=[
                    LLMModelPublic(
                        id="openai/gpt-4o-mini",
                        provider="openai",
                        provider_label="OpenAI",
                        model="gpt-4o-mini",
                        label="GPT 4o mini",
                        is_default=True,
                        is_recommended=True,
                        max_input_tokens=128000,
                        max_output_tokens=16384,
                    )
                ],
            )
        ],
    )
    monkeypatch.setattr(config_route, "get_available_llm_models", lambda: catalog)

    r = client.get(
        f"{settings.API_V1_STR}/config/llm-models",
        cookies=auth_cookies,
    )

    assert r.status_code == 200
    payload = r.json()
    assert payload["default_model"] == "openai/gpt-4o-mini"
    assert payload["count"] == 1
    assert payload["data"][0]["provider"] == "openai"
    assert payload["data"][0]["models"][0]["id"] == "openai/gpt-4o-mini"


def test_available_metrics_includes_custom_metrics(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    before = client.get(
        f"{settings.API_V1_STR}/config/available-metrics",
        cookies=auth_cookies,
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
        cookies=auth_cookies,
    )
    assert create_r.status_code == 200

    after = client.get(
        f"{settings.API_V1_STR}/config/available-metrics",
        cookies=auth_cookies,
    )
    assert after.status_code == 200
    payload = after.json()
    assert payload["count"] == count_before + 1
    metric_names = {m["name"] for m in payload["data"]}
    assert name in metric_names
    assert "tool_routing" in metric_names
