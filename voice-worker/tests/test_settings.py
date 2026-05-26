"""Tests for worker public URL resolution and settings."""

from __future__ import annotations

import pytest

from voice_runner.settings import WorkerSettings, resolved_public_base_url


def test_resolved_public_base_url_explicit() -> None:
    settings = WorkerSettings(VOICE_PUBLIC_BASE_URL="https://abc.ngrok-free.app/")
    assert resolved_public_base_url(settings) == "https://abc.ngrok-free.app"


def test_resolved_public_base_url_kubernetes_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POD_NAME", "connexity-voice-worker-2")
    monkeypatch.delenv("VOICE_PUBLIC_BASE_URL", raising=False)
    settings = WorkerSettings(
        VOICE_PUBLIC_BASE_URL=None,
        VOICE_WORKER_PUBLIC_HOST_SUFFIX="voice.example.com",
    )
    assert (
        resolved_public_base_url(settings)
        == "https://connexity-voice-worker-2.voice.example.com"
    )


def test_resolved_public_base_url_missing_config() -> None:
    settings = WorkerSettings(
        VOICE_PUBLIC_BASE_URL=None,
        VOICE_WORKER_PUBLIC_HOST_SUFFIX=None,
    )
    with pytest.raises(ValueError, match="VOICE_PUBLIC_BASE_URL"):
        resolved_public_base_url(settings)
