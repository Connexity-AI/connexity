import logging
import re
import time
from typing import cast

import litellm
from litellm.utils import get_valid_models
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

LLM_MODELS_CACHE_TTL_SECONDS = 300


class LLMModelPublic(BaseModel):
    id: str = Field(description="Full LiteLLM routing id, e.g. openai/gpt-4o-mini")
    provider: str = Field(description="LiteLLM provider key, e.g. openai")
    provider_label: str = Field(description="Human-readable provider label")
    model: str = Field(description="Provider-local model id")
    label: str = Field(description="Human-readable model label")
    is_default: bool = Field(
        description="Whether this is the default model for the provider"
    )
    is_recommended: bool = Field(
        description="Whether this model should be featured first"
    )
    max_input_tokens: int | None = Field(
        default=None, description="Known input context window"
    )
    max_output_tokens: int | None = Field(
        default=None, description="Known output token limit"
    )


class LLMModelProviderPublic(BaseModel):
    provider: str = Field(description="LiteLLM provider key")
    label: str = Field(description="Human-readable provider label")
    default_model: str | None = Field(
        default=None, description="Full LiteLLM routing id for this provider"
    )
    models: list[LLMModelPublic] = Field(description="Selectable chat models")


class LLMModelsPublic(BaseModel):
    data: list[LLMModelProviderPublic] = Field(
        description="Available LLM models by provider"
    )
    count: int = Field(description="Total number of selectable models")
    default_model: str = Field(description="Global default full LiteLLM routing id")


_MODEL_COST = cast("dict[str, dict[str, object]]", litellm.model_cost)
_CatalogCache = tuple[float, LLMModelsPublic]
_catalog_cache: _CatalogCache | None = None


def clear_llm_model_catalog_cache() -> None:
    global _catalog_cache
    _catalog_cache = None


def get_available_llm_models() -> LLMModelsPublic:
    global _catalog_cache
    now = time.monotonic()
    if _catalog_cache is not None:
        cached_at, cached_catalog = _catalog_cache
        if now - cached_at < LLM_MODELS_CACHE_TTL_SECONDS:
            return cached_catalog

    catalog = _build_model_catalog()
    if catalog.count > 0:
        _catalog_cache = (now, catalog)
    return catalog


def _build_model_catalog() -> LLMModelsPublic:
    providers = _group_models_by_provider(_get_available_model_ids())
    total = sum(len(provider.models) for provider in providers)
    return LLMModelsPublic(
        data=providers, count=total, default_model=settings.default_llm_id
    )


def _get_available_model_ids() -> list[str]:
    live_models = _safe_get_valid_models(check_provider_endpoint=True)
    if live_models:
        return live_models
    return _safe_get_valid_models(check_provider_endpoint=False)


def _safe_get_valid_models(check_provider_endpoint: bool) -> list[str]:
    try:
        return get_valid_models(check_provider_endpoint=check_provider_endpoint)
    except Exception as exc:
        source = "provider endpoint" if check_provider_endpoint else "LiteLLM catalog"
        logger.warning("Failed to load models from %s: %s", source, exc)
        return []


def _group_models_by_provider(raw_models: list[str]) -> list[LLMModelProviderPublic]:
    grouped: dict[str, list[LLMModelPublic]] = {}
    seen: set[str] = set()

    for raw_model in raw_models:
        model_id = raw_model.strip()
        if not model_id:
            continue

        metadata = _model_metadata(model_id)
        if not _is_chat_model(metadata):
            continue

        provider = _model_provider(model_id, metadata)
        if provider is None:
            continue

        bare_model = _bare_model_id(provider, model_id)
        full_id = _full_model_id(provider, bare_model)
        if full_id in seen:
            continue
        seen.add(full_id)

        grouped.setdefault(provider, []).append(
            LLMModelPublic(
                id=full_id,
                provider=provider,
                provider_label=_provider_label(provider),
                model=bare_model,
                label=bare_model,
                is_default=full_id == settings.default_llm_id,
                is_recommended=False,
                max_input_tokens=_int_metadata(metadata, "max_input_tokens"),
                max_output_tokens=_int_metadata(metadata, "max_output_tokens")
                or _int_metadata(metadata, "max_tokens"),
            )
        )

    return [
        LLMModelProviderPublic(
            provider=provider,
            label=_provider_label(provider),
            default_model=_provider_default(models),
            models=sorted(models, key=_newest_model_sort_key, reverse=True),
        )
        for provider, models in grouped.items()
    ]


def _full_model_id(provider: str, model: str) -> str:
    if model.startswith(f"{provider}/") or "/" in model:
        return model
    return f"{provider}/{model}"


def _bare_model_id(provider: str, full_model_id: str) -> str:
    prefix = f"{provider}/"
    if full_model_id.startswith(prefix):
        return full_model_id.removeprefix(prefix)
    return full_model_id


def _model_metadata(model_id: str) -> dict[str, object]:
    bare_model = model_id.split("/", 1)[1] if "/" in model_id else model_id
    return _MODEL_COST.get(model_id) or _MODEL_COST.get(bare_model) or {}


def _model_provider(model_id: str, metadata: dict[str, object]) -> str | None:
    provider = metadata.get("litellm_provider")
    if isinstance(provider, str) and provider.strip():
        return _normalize_provider(provider)
    if "/" in model_id:
        return model_id.split("/", 1)[0]
    return None


def _normalize_provider(provider: str) -> str:
    return provider.removesuffix("-language-models")


def _provider_label(provider: str) -> str:
    known_labels = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "azure": "Azure",
        "gemini": "Gemini",
        "vertex_ai": "Vertex AI",
    }
    if provider in known_labels:
        return known_labels[provider]
    return provider.replace("_", " ").replace("-", " ").title()


def _provider_default(models: list[LLMModelPublic]) -> str | None:
    if not models:
        return None
    default = next((model.id for model in models if model.is_default), None)
    return default or models[0].id


def _newest_model_sort_key(
    model: LLMModelPublic,
) -> tuple[tuple[int, ...], tuple[int, ...], str]:
    version_numbers = _model_version_numbers(model.model)
    date_numbers = tuple(
        int(part)
        for match in re.findall(r"(20\d{2})[-_]?(\d{2})?[-_]?(\d{2})?", model.model)
        for part in match
        if part
    )
    return version_numbers, date_numbers, model.model


def _model_version_numbers(model: str) -> tuple[int, ...]:
    parts = re.split(r"[-_/]", model.lower())
    numbers: list[int] = []
    started = False
    for part in parts:
        part_numbers = [int(match) for match in re.findall(r"\d+", part)]
        if not part_numbers:
            if started:
                break
            continue
        for number in part_numbers:
            if number >= 100:
                return tuple(numbers)
            numbers.append(number)
        started = True
    return tuple(numbers)


def _is_chat_model(metadata: dict[str, object]) -> bool:
    supported_endpoints = metadata.get("supported_endpoints")
    if isinstance(supported_endpoints, list):
        return (
            "/v1/chat/completions" in supported_endpoints
            or "/v1/completions" in supported_endpoints
        )

    return metadata.get("mode") == "chat" and (
        "max_input_tokens" in metadata or "max_tokens" in metadata
    )


def _int_metadata(metadata: dict[str, object], key: str) -> int | None:
    value = metadata.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None
