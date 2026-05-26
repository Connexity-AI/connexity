"""HTTP endpoint smoke tests (no Twilio/Postgres)."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def voice_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("VOICE_PUBLIC_BASE_URL", "https://voice.example.test")

    async def _noop_worker_loop(stop: object, worker_settings: object) -> None:
        _ = worker_settings
        assert stop is not None

    monkeypatch.setattr("voice_runner.main.worker_loop", _noop_worker_loop)

    from voice_runner.main import app  # noqa: PLC0415

    with TestClient(app) as client:
        yield client


def test_health_endpoint(voice_client: TestClient) -> None:
    response = voice_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_twiml_returns_media_stream_connect_xml(voice_client: TestClient) -> None:
    job_id = uuid.uuid4()
    response = voice_client.get(f"/twiml/{job_id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    body = response.text
    assert "wss://voice.example.test/ws" in body
    assert str(job_id) in body


def test_twilio_start_handshake_json_parsing() -> None:
    import json

    raw = json.dumps(
        {
            "event": "start",
            "sequenceNumber": "1",
            "start": {
                "callSid": "CA_test",
                "streamSid": "MZ_test",
                "customParameters": {"job_id": "550e8400-e29b-41d4-a716-446655440000"},
            },
        }
    )
    handshake = json.loads(raw)
    assert handshake.get("event") == "start"
    start = handshake["start"]
    assert start["callSid"] == "CA_test"
    assert start["streamSid"] == "MZ_test"
    assert start["customParameters"]["job_id"] == "550e8400-e29b-41d4-a716-446655440000"
