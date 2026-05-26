"""Lightweight constructors / decoder checks (no Twilio/network)."""

from __future__ import annotations

import wave
from io import BytesIO
from types import SimpleNamespace

import pytest

from voice_runner.bot.dtmf_pcm import concat_framed_dtmf_pcm16


def pcm16mono_to_wav(pcm: bytes, sample_rate: int = 8000) -> bytes:
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    buf.seek(0)
    return buf.read()


@pytest.mark.parametrize(
    ("stt_prov", "tts_prov", "stt_model", "tts_model", "tts_voice"),
    [
        ("deepgram", "elevenlabs", "nova-3-general", "eleven_flash_v2_5", "voice-id"),
        ("openai", "openai", "whisper-1", "tts-1", "alloy"),
        ("cartesia", "cartesia", "ink-whisper", "sonic-3", "sonic-english"),
    ],
)
def test_stt_tts_factory_builds_providers(
    monkeypatch: pytest.MonkeyPatch,
    stt_prov: str,
    tts_prov: str,
    stt_model: str,
    tts_model: str,
    tts_voice: str,
) -> None:
    import voice_runner.services as voice_services  # noqa: PLC0415

    monkeypatch.setattr(voice_services.connexity_settings, "DEEPGRAM_API_KEY", "stub")
    monkeypatch.setattr(voice_services.connexity_settings, "OPENAI_API_KEY", "stub")
    monkeypatch.setattr(voice_services.connexity_settings, "ELEVENLABS_API_KEY", "stub")
    monkeypatch.setattr(voice_services.connexity_settings, "CARTESIA_API_KEY", "stub")

    from voice_runner.services import build_stt_tts_services  # noqa: PLC0415
    from voice_runner.settings import WorkerSettings  # noqa: PLC0415

    job = SimpleNamespace(
        stt_provider=stt_prov,
        stt_model=stt_model,
        tts_provider=tts_prov,
        tts_model=tts_model,
        tts_voice_id=tts_voice,
    )

    stt, tts = build_stt_tts_services(
        job,
        run_config=None,
        shared_settings=WorkerSettings(),
    )

    assert stt is not None
    assert tts is not None


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_native_llm_service_factory(
    provider: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import voice_runner.services as voice_services  # noqa: PLC0415

    monkeypatch.setattr(voice_services.connexity_settings, "OPENAI_API_KEY", "sk-stub")
    monkeypatch.setattr(voice_services.connexity_settings, "ANTHROPIC_API_KEY", "stub")
    if provider == "google":
        monkeypatch.setattr(
            voice_services.connexity_settings, "GOOGLE_GENAI_API_KEY", "stub"
        )

    from app.models.enums import SimulatorMode  # noqa: PLC0415

    from voice_runner.services import build_llm_service  # noqa: PLC0415
    from voice_runner.settings import WorkerSettings  # noqa: PLC0415

    model_name = (
        "gpt-4.1-mini"
        if provider == "openai"
        else (
            "claude-sonnet-4-20250514"
            if provider == "anthropic"
            else "gemini-2.0-flash"
        )
    )

    fake_run_cfg = SimpleNamespace(
        user_simulator=SimpleNamespace(
            mode=SimulatorMode.LLM,
            provider=provider,
            model=model_name,
            temperature=0.55,
            stt=None,
            tts=None,
        ),
    )

    tc = SimpleNamespace(
        persona_context="caller persona",
        user_context={"scenario": "order lookup"},
        expected_outcomes=None,
    )

    worker = WorkerSettings()

    llm = build_llm_service(
        run_config=fake_run_cfg,
        test_case=tc,
        persona_system_prompt="SYSTEM",
        worker_settings=worker,
    )
    lowered = llm.__class__.__name__.lower()
    match provider:
        case "openai":
            assert "openai" in lowered
        case "anthropic":
            assert "anthropic" in lowered
        case "google":
            assert "google" in lowered


def test_connexity_synthetic_dtmf_pcm_decodes() -> None:
    from app.services.dtmf import decode_dtmf_from_audio_bytes  # noqa: PLC0415

    framed = "*123#"
    pcm = concat_framed_dtmf_pcm16(framed)
    wav = pcm16mono_to_wav(pcm)

    decoded = decode_dtmf_from_audio_bytes(wav, content_type="audio/wav")

    assert decoded.success
    assert decoded.digits == framed


def test_keypad_validator_rejects_invalid_chars() -> None:
    from voice_runner.bot.dtmf_audio_emitter import (
        keypad_for_dtmf_char,  # noqa: PLC0415
    )

    with pytest.raises(ValueError):
        keypad_for_dtmf_char("A")
