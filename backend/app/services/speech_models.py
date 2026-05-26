"""STT/TTS model catalogs for voice persona configuration (Pipecat-aligned providers)."""

import logging
import time
from collections.abc import Callable
from typing import Any, Literal, NamedTuple

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.elevenlabs import list_elevenlabs_voices

logger = logging.getLogger(__name__)

SPEECH_MODELS_CACHE_TTL_SECONDS = 300

SpeechModality = Literal["stt", "tts"]

_PROVIDER_LABELS: dict[str, str] = {
    "deepgram": "Deepgram",
    "openai": "OpenAI",
    "elevenlabs": "ElevenLabs",
    "cartesia": "Cartesia",
}

_OPENAI_STT_MODELS: list[tuple[str, str]] = [
    ("gpt-4o-transcribe", "GPT-4o Transcribe"),
    ("gpt-4o-mini-transcribe", "GPT-4o Mini Transcribe"),
    ("whisper-1", "Whisper"),
]

_OPENAI_TTS_MODELS: list[tuple[str, str]] = [
    ("gpt-4o-mini-tts", "GPT-4o Mini TTS"),
    ("tts-1", "TTS-1"),
]

_OPENAI_TTS_VOICES: list[tuple[str, str]] = [
    ("alloy", "Alloy"),
    ("ash", "Ash"),
    ("ballad", "Ballad"),
    ("cedar", "Cedar"),
    ("coral", "Coral"),
    ("echo", "Echo"),
    ("fable", "Fable"),
    ("marin", "Marin"),
    ("nova", "Nova"),
    ("onyx", "Onyx"),
    ("sage", "Sage"),
    ("shimmer", "Shimmer"),
    ("verse", "Verse"),
]

# Text-to-speech only (see https://elevenlabs.io/docs/overview/models).
# Turbo v2/v2.5 are deprecated in favor of Flash; STS/TTV/Scribe models are excluded.
_ELEVENLABS_TTS_MODELS: list[tuple[str, str]] = [
    ("eleven_v3", "Eleven v3"),
    ("eleven_flash_v2_5", "Flash v2.5"),
    ("eleven_flash_v2", "Flash v2"),
    ("eleven_multilingual_v2", "Multilingual v2"),
]

_CARTESIA_STT_MODELS: list[tuple[str, str]] = [
    ("ink-whisper", "Ink Whisper"),
]

_CARTESIA_TTS_MODELS: list[tuple[str, str]] = [
    ("sonic-3", "Sonic 3"),
]

_CARTESIA_API_VERSION = "2024-11-13"
_DEEPGRAM_MODELS_URL = "https://api.deepgram.com/v1/models"
_CARTESIA_VOICES_URL = "https://api.cartesia.ai/voices"


class _DeepgramTtsVoice(NamedTuple):
    """TTS architecture (Pipecat model) plus selectable voice id from Deepgram /v1/models."""

    architecture: str
    voice_id: str
    label: str


class SpeechModelPublic(BaseModel):
    id: str = Field(description="Full routing id, e.g. deepgram/nova-3-general")
    provider: str = Field(description="Pipecat provider key")
    provider_label: str = Field(description="Human-readable provider label")
    model: str = Field(description="Provider-local model id")
    label: str = Field(description="Human-readable model label")
    is_default: bool = Field(
        description="Default model for this provider in the catalog"
    )


class SpeechModelProviderPublic(BaseModel):
    provider: str = Field(description="Pipecat provider key")
    label: str = Field(description="Human-readable provider label")
    default_model: str | None = Field(
        default=None, description="Full routing id for provider default"
    )
    models: list[SpeechModelPublic] = Field(description="Selectable models")


class SpeechModelsPublic(BaseModel):
    data: list[SpeechModelProviderPublic] = Field(
        description="Available speech models by provider"
    )
    count: int = Field(description="Total selectable models")
    default_model: str | None = Field(
        default=None, description="Global default full routing id when configured"
    )


class VoicePublic(BaseModel):
    id: str = Field(description="Voice id passed to Pipecat TTS Settings.voice")
    label: str = Field(description="Human-readable voice label")
    preview_url: str | None = Field(
        default=None, description="Optional preview audio URL when available"
    )


class VoicesPublic(BaseModel):
    data: list[VoicePublic] = Field(description="Selectable voices")
    count: int = Field(description="Number of voices")
    default_voice_id: str | None = Field(
        default=None, description="Suggested default voice for provider/model"
    )


_CatalogCache = tuple[float, SpeechModelsPublic]
_VoicesCacheKey = tuple[str, str]
_VoicesCache = tuple[float, VoicesPublic]

_stt_catalog_cache: _CatalogCache | None = None
_tts_catalog_cache: _CatalogCache | None = None
_voices_cache: dict[_VoicesCacheKey, _VoicesCache] = {}


def clear_speech_model_catalog_cache() -> None:
    global _stt_catalog_cache, _tts_catalog_cache, _voices_cache
    _stt_catalog_cache = None
    _tts_catalog_cache = None
    _voices_cache = {}


def get_available_stt_models() -> SpeechModelsPublic:
    return _get_cached_catalog("stt", _build_stt_catalog)


def get_available_tts_models() -> SpeechModelsPublic:
    return _get_cached_catalog("tts", _build_tts_catalog)


def get_available_tts_voices(*, provider: str, model: str) -> VoicesPublic:
    provider_key = provider.strip().lower()
    model_key = model.strip()
    cache_key: _VoicesCacheKey = (provider_key, model_key)
    now = time.monotonic()
    cached = _voices_cache.get(cache_key)
    if cached is not None:
        cached_at, catalog = cached
        if now - cached_at < SPEECH_MODELS_CACHE_TTL_SECONDS:
            return catalog

    catalog = _build_voices_catalog(provider=provider_key, model=model_key)
    if catalog.count > 0:
        _voices_cache[cache_key] = (now, catalog)
    return catalog


def _get_cached_catalog(
    modality: SpeechModality,
    builder: Callable[[], SpeechModelsPublic],
) -> SpeechModelsPublic:
    global _stt_catalog_cache, _tts_catalog_cache
    now = time.monotonic()
    cache = _stt_catalog_cache if modality == "stt" else _tts_catalog_cache
    if cache is not None:
        cached_at, cached_catalog = cache
        if now - cached_at < SPEECH_MODELS_CACHE_TTL_SECONDS:
            return cached_catalog

    catalog = builder()
    if catalog.count > 0:
        entry = (now, catalog)
        if modality == "stt":
            _stt_catalog_cache = entry
        else:
            _tts_catalog_cache = entry
    return catalog


def _build_stt_catalog() -> SpeechModelsPublic:
    providers: list[SpeechModelProviderPublic] = []
    if settings.DEEPGRAM_API_KEY:
        providers.extend(_deepgram_stt_providers(settings.DEEPGRAM_API_KEY))
    if settings.OPENAI_API_KEY:
        providers.append(_static_provider("openai", _OPENAI_STT_MODELS))
    if settings.CARTESIA_API_KEY:
        providers.append(_static_provider("cartesia", _CARTESIA_STT_MODELS))
    return _finalize_catalog(providers, modality="stt")


def _build_tts_catalog() -> SpeechModelsPublic:
    providers: list[SpeechModelProviderPublic] = []
    if settings.DEEPGRAM_API_KEY:
        providers.extend(_deepgram_tts_providers(settings.DEEPGRAM_API_KEY))
    if settings.OPENAI_API_KEY:
        providers.append(_static_provider("openai", _OPENAI_TTS_MODELS))
    if settings.ELEVENLABS_API_KEY:
        providers.append(_static_provider("elevenlabs", _ELEVENLABS_TTS_MODELS))
    if settings.CARTESIA_API_KEY:
        providers.append(_static_provider("cartesia", _CARTESIA_TTS_MODELS))
    return _finalize_catalog(providers, modality="tts")


def _build_voices_catalog(*, provider: str, model: str) -> VoicesPublic:
    if provider == "openai":
        return _static_voices(_OPENAI_TTS_VOICES)
    if provider == "elevenlabs" and settings.ELEVENLABS_API_KEY:
        return _elevenlabs_voices()
    if provider == "deepgram" and settings.DEEPGRAM_API_KEY:
        return _deepgram_voices(api_key=settings.DEEPGRAM_API_KEY, model=model)
    if provider == "cartesia" and settings.CARTESIA_API_KEY:
        return _cartesia_voices()
    return VoicesPublic(data=[], count=0, default_voice_id=None)


def _finalize_catalog(
    providers: list[SpeechModelProviderPublic],
    *,
    modality: SpeechModality,
) -> SpeechModelsPublic:
    total = sum(len(p.models) for p in providers)
    default_model = _global_default_model(modality)
    if default_model:
        _mark_default(providers, default_model)
    elif providers and providers[0].models:
        first_id = providers[0].models[0].id
        _mark_default(providers, first_id)
        default_model = first_id
    return SpeechModelsPublic(data=providers, count=total, default_model=default_model)


def _global_default_model(modality: SpeechModality) -> str | None:
    if modality == "stt":
        provider = (settings.DEFAULT_STT_PROVIDER or "").strip()
        model = (settings.DEFAULT_STT_MODEL or "").strip()
    else:
        provider = (settings.DEFAULT_TTS_PROVIDER or "").strip()
        model = (settings.DEFAULT_TTS_MODEL or "").strip()
    if provider and model:
        return _full_model_id(provider, model)
    return None


def _mark_default(providers: list[SpeechModelProviderPublic], full_id: str) -> None:
    for group in providers:
        for entry in group.models:
            entry.is_default = entry.id == full_id
        default = next((m.id for m in group.models if m.is_default), None)
        group.default_model = default or group.default_model


def _static_provider(
    provider: str,
    models: list[tuple[str, str]],
) -> SpeechModelProviderPublic:
    entries = [
        _speech_model_entry(provider, model_id, label, is_default=False)
        for model_id, label in models
    ]
    default_id = entries[0].id if entries else None
    return SpeechModelProviderPublic(
        provider=provider,
        label=_provider_label(provider),
        default_model=default_id,
        models=entries,
    )


def _speech_model_entry(
    provider: str,
    model_id: str,
    label: str,
    *,
    is_default: bool,
) -> SpeechModelPublic:
    full_id = _full_model_id(provider, model_id)
    return SpeechModelPublic(
        id=full_id,
        provider=provider,
        provider_label=_provider_label(provider),
        model=model_id,
        label=label,
        is_default=is_default,
    )


def _full_model_id(provider: str, model: str) -> str:
    if model.startswith(f"{provider}/"):
        return model
    return f"{provider}/{model}"


def _provider_label(provider: str) -> str:
    return _PROVIDER_LABELS.get(provider, provider.replace("_", " ").title())


def _dedupe_model_tuples(models: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for model_id, label in models:
        if model_id in seen:
            continue
        seen.add(model_id)
        out.append((model_id, label))
    return out


def _deepgram_stt_providers(api_key: str) -> list[SpeechModelProviderPublic]:
    stt_models, _ = _fetch_deepgram_model_lists(api_key)
    stt_models = _dedupe_model_tuples(stt_models)
    if not stt_models:
        return []
    entries = [
        _speech_model_entry("deepgram", model_id, label, is_default=False)
        for model_id, label in stt_models
    ]
    return [
        SpeechModelProviderPublic(
            provider="deepgram",
            label=_provider_label("deepgram"),
            default_model=entries[0].id if entries else None,
            models=entries,
        )
    ]


def _deepgram_tts_providers(api_key: str) -> list[SpeechModelProviderPublic]:
    tts_voices = _fetch_deepgram_tts_voices(api_key)
    if not tts_voices:
        return [
            SpeechModelProviderPublic(
                provider="deepgram",
                label=_provider_label("deepgram"),
                default_model=None,
                models=[
                    _speech_model_entry(
                        "deepgram",
                        "aura",
                        "Aura",
                        is_default=True,
                    )
                ],
            )
        ]
    architectures = _dedupe_model_tuples(
        [(v.architecture, _architecture_label(v.architecture)) for v in tts_voices]
    )
    entries = [
        _speech_model_entry("deepgram", arch_id, label, is_default=False)
        for arch_id, label in architectures
    ]
    return [
        SpeechModelProviderPublic(
            provider="deepgram",
            label=_provider_label("deepgram"),
            default_model=entries[0].id if entries else None,
            models=entries,
        )
    ]


def _fetch_deepgram_models_payload(api_key: str) -> dict[str, Any] | None:
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                _DEEPGRAM_MODELS_URL,
                headers={"Authorization": f"Token {api_key}"},
            )
        if response.status_code != 200:
            logger.warning(
                "Deepgram models API returned %s: %s",
                response.status_code,
                response.text[:200],
            )
            return None
        payload = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Failed to load Deepgram models: %s", exc)
        return None
    return payload if isinstance(payload, dict) else None


def _fetch_deepgram_model_lists(
    api_key: str,
) -> tuple[list[tuple[str, str]], list[_DeepgramTtsVoice]]:
    payload = _fetch_deepgram_models_payload(api_key)
    if payload is None:
        return [], []

    stt: list[tuple[str, str]] = []
    for item in payload.get("stt") or []:
        if not isinstance(item, dict):
            continue
        name = _deepgram_model_name(item)
        if name:
            stt.append((name, name))
    return stt, _parse_deepgram_tts_payload(payload)


def _fetch_deepgram_tts_voices(api_key: str) -> list[_DeepgramTtsVoice]:
    payload = _fetch_deepgram_models_payload(api_key)
    if payload is None:
        return []
    return _parse_deepgram_tts_payload(payload)


def _parse_deepgram_tts_payload(payload: dict[str, Any]) -> list[_DeepgramTtsVoice]:
    voices: list[_DeepgramTtsVoice] = []
    seen: set[tuple[str, str]] = set()
    for item in payload.get("tts") or []:
        if not isinstance(item, dict):
            continue
        parsed = _parse_deepgram_tts_item(item)
        if parsed is None:
            continue
        key = (parsed.architecture, parsed.voice_id)
        if key in seen:
            continue
        seen.add(key)
        voices.append(parsed)
    return voices


def _parse_deepgram_tts_item(item: dict[str, Any]) -> _DeepgramTtsVoice | None:
    architecture = item.get("architecture")
    if not isinstance(architecture, str) or not architecture.strip():
        return None
    voice_id = _deepgram_model_name(item)
    if not voice_id:
        return None
    name = item.get("name")
    label = name.strip() if isinstance(name, str) and name.strip() else voice_id
    return _DeepgramTtsVoice(architecture.strip(), voice_id, label)


def _architecture_label(architecture: str) -> str:
    return architecture.replace("-", " ").replace("_", " ").title()


def _deepgram_model_name(item: dict[str, Any]) -> str | None:
    for key in ("canonical_name", "name", "model"):
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def _deepgram_voices(*, api_key: str, model: str) -> VoicesPublic:
    tts_voices = _fetch_deepgram_tts_voices(api_key)
    if not tts_voices:
        return VoicesPublic(data=[], count=0, default_voice_id=None)
    bare_model = model.removeprefix("deepgram/") if model else model
    filtered = [v for v in tts_voices if v.architecture == bare_model]
    if not filtered:
        return VoicesPublic(data=[], count=0, default_voice_id=None)
    return _static_voices([(v.voice_id, v.label) for v in filtered])


def _elevenlabs_voices() -> VoicesPublic:
    api_key = settings.ELEVENLABS_API_KEY
    if not api_key:
        return VoicesPublic(data=[], count=0, default_voice_id=None)
    summaries = list_elevenlabs_voices(api_key)
    voices = [
        VoicePublic(
            id=v.voice_id, label=v.name or v.voice_id, preview_url=v.preview_url
        )
        for v in summaries
    ]
    default = (settings.DEFAULT_TTS_VOICE_ID or "").strip() or (
        voices[0].id if voices else None
    )
    return VoicesPublic(data=voices, count=len(voices), default_voice_id=default)


def _cartesia_voices() -> VoicesPublic:
    api_key = settings.CARTESIA_API_KEY
    if not api_key:
        return VoicesPublic(data=[], count=0, default_voice_id=None)
    voices: list[VoicePublic] = []
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                _CARTESIA_VOICES_URL,
                headers={
                    "X-API-Key": api_key,
                    "Cartesia-Version": _CARTESIA_API_VERSION,
                },
                params={"limit": 100},
            )
        if response.status_code != 200:
            logger.warning(
                "Cartesia voices API returned %s",
                response.status_code,
            )
            return VoicesPublic(data=[], count=0, default_voice_id=None)
        payload = response.json()
        items = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            return VoicesPublic(data=[], count=0, default_voice_id=None)
        for item in items:
            if not isinstance(item, dict):
                continue
            voice_id = item.get("id")
            if not voice_id:
                continue
            name = item.get("name") or str(voice_id)
            preview = item.get("preview_file_url")
            preview_url = preview if isinstance(preview, str) else None
            voices.append(
                VoicePublic(id=str(voice_id), label=str(name), preview_url=preview_url)
            )
    except httpx.HTTPError as exc:
        logger.warning("Failed to load Cartesia voices: %s", exc)
        return VoicesPublic(data=[], count=0, default_voice_id=None)

    default = (settings.DEFAULT_TTS_VOICE_ID or "").strip() or (
        voices[0].id if voices else None
    )
    return VoicesPublic(data=voices, count=len(voices), default_voice_id=default)


def _static_voices(pairs: list[tuple[str, str]]) -> VoicesPublic:
    voices = [VoicePublic(id=vid, label=label) for vid, label in pairs]
    default = (settings.DEFAULT_TTS_VOICE_ID or "").strip() or (
        voices[0].id if voices else None
    )
    return VoicesPublic(data=voices, count=len(voices), default_voice_id=default)
