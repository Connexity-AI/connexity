from pytest import MonkeyPatch

from app.core.config import settings
from app.services import speech_models


def test_stt_catalog_openai_only(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DEEPGRAM_API_KEY", None)
    monkeypatch.setattr(settings, "CARTESIA_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", None)
    speech_models.clear_speech_model_catalog_cache()

    catalog = speech_models.get_available_stt_models()
    assert catalog.count >= 1
    assert any(p.provider == "openai" for p in catalog.data)
    assert any("gpt-4o-transcribe" in m.model for p in catalog.data for m in p.models)


def test_tts_catalog_empty_without_keys(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DEEPGRAM_API_KEY", None)
    monkeypatch.setattr(settings, "CARTESIA_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", None)
    speech_models.clear_speech_model_catalog_cache()

    catalog = speech_models.get_available_tts_models()
    assert catalog.count == 0
    assert catalog.data == []


def test_openai_tts_voices_static() -> None:
    voices = speech_models.get_available_tts_voices(provider="openai", model="tts-1")
    assert voices.count == len(speech_models._OPENAI_TTS_VOICES)
    assert any(v.id == "nova" for v in voices.data)


def test_deepgram_tts_catalog_uses_architecture_not_voice(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DEEPGRAM_API_KEY", "test-key")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", None)
    monkeypatch.setattr(settings, "CARTESIA_API_KEY", None)
    speech_models.clear_speech_model_catalog_cache()

    def fake_tts_voices(_api_key: str) -> list[speech_models._DeepgramTtsVoice]:
        return [
            speech_models._DeepgramTtsVoice("aura", "aura-angus-en", "Angus"),
            speech_models._DeepgramTtsVoice("aura", "aura-2-helena-en", "Helena"),
        ]

    monkeypatch.setattr(speech_models, "_fetch_deepgram_tts_voices", fake_tts_voices)
    monkeypatch.setattr(
        speech_models,
        "_fetch_deepgram_model_lists",
        lambda _api_key: ([], fake_tts_voices(_api_key)),
    )

    catalog = speech_models.get_available_tts_models()
    deepgram = next(p for p in catalog.data if p.provider == "deepgram")
    assert len(deepgram.models) == 1
    assert deepgram.models[0].model == "aura"

    voices = speech_models.get_available_tts_voices(provider="deepgram", model="aura")
    assert voices.count == 2
    assert {v.id for v in voices.data} == {"aura-angus-en", "aura-2-helena-en"}
