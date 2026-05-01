from pytest import MonkeyPatch

from app.core.config import settings
from app.services import llm_models


def test_catalog_falls_back_to_static_models_and_filters_to_chat(
    monkeypatch: MonkeyPatch,
) -> None:
    calls: list[bool | None] = []

    def fake_get_valid_models(
        check_provider_endpoint: bool | None = None,
        custom_llm_provider: str | None = None,
        litellm_params: object | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> list[str]:
        _ = (custom_llm_provider, litellm_params, api_key, api_base)
        calls.append(check_provider_endpoint)
        if check_provider_endpoint:
            return []
        return ["gpt-4o-mini", "text-embedding-3-small"]

    monkeypatch.setattr(llm_models, "get_valid_models", fake_get_valid_models)
    monkeypatch.setattr(
        llm_models,
        "_MODEL_COST",
        {
            "gpt-4o-mini": {
                "litellm_provider": "openai",
                "mode": "chat",
                "max_input_tokens": 128000,
                "max_output_tokens": 16384,
            },
            "text-embedding-3-small": {
                "litellm_provider": "openai",
                "mode": "embedding",
            },
        },
    )
    llm_models.clear_llm_model_catalog_cache()

    catalog = llm_models.get_available_llm_models()

    assert calls == [True, False]
    assert catalog.count == 1
    assert catalog.default_model == settings.default_llm_id
    assert catalog.data[0].provider == "openai"
    assert catalog.data[0].models[0].id == "openai/gpt-4o-mini"
    assert catalog.data[0].models[0].label == "gpt-4o-mini"
    assert catalog.data[0].models[0].max_input_tokens == 128000


def test_catalog_sorts_models_newest_first(monkeypatch: MonkeyPatch) -> None:
    def fake_get_valid_models(
        check_provider_endpoint: bool | None = None,
        custom_llm_provider: str | None = None,
        litellm_params: object | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> list[str]:
        _ = (
            check_provider_endpoint,
            custom_llm_provider,
            litellm_params,
            api_key,
            api_base,
        )
        return ["gpt-4", "gpt-5.5", "gpt-5.4", "gpt-3.5-turbo"]

    monkeypatch.setattr(llm_models, "get_valid_models", fake_get_valid_models)
    monkeypatch.setattr(
        llm_models,
        "_MODEL_COST",
        {
            model: {
                "litellm_provider": "openai",
                "mode": "chat",
                "max_input_tokens": 128000,
            }
            for model in ["gpt-4", "gpt-5.5", "gpt-5.4", "gpt-3.5-turbo"]
        },
    )
    llm_models.clear_llm_model_catalog_cache()

    catalog = llm_models.get_available_llm_models()

    assert [model.model for model in catalog.data[0].models] == [
        "gpt-5.5",
        "gpt-5.4",
        "gpt-4",
        "gpt-3.5-turbo",
    ]
