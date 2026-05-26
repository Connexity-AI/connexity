import socket

import pytest
import respx
from httpx import Response

from app.services.dtmf import (
    allocate_dtmf_code,
    decode_dtmf_from_audio_bytes,
    decode_dtmf_from_audio_url,
    format_dtmf_code,
    validate_connexity_dtmf_code,
)
from app.services.dtmf_audio import UnsafeAudioUrlError, validate_audio_download_url
from app.tests.services.dtmf_fixtures import (
    build_dtmf_alaw_wav_bytes,
    build_dtmf_mp3_bytes,
    build_dtmf_mulaw_wav_bytes,
    build_dtmf_wav_bytes,
    build_malformed_wav_bytes,
    build_speech_like_wav_bytes,
    example_connexity_code,
    ffmpeg_available,
)

pytestmark_codec = pytest.mark.skipif(
    not ffmpeg_available(),
    reason="ffmpeg is required",
)


@pytest.mark.parametrize(
    ("audio_url", "expected_code"),
    [
        ("mock-dtmf://*246#", "*246#"),
        (
            "https://example.com/recordings/mock-dtmf/*246%23/call.wav",
            "*246#",
        ),
        (
            "https://example.com/recording.wav?connexity_mock_dtmf=*33%23",
            "*33#",
        ),
    ],
)
def test_decode_dtmf_from_audio_url_mock_success(
    audio_url: str,
    expected_code: str,
) -> None:
    result = decode_dtmf_from_audio_url(audio_url)
    assert result.success
    assert result.digits == expected_code
    assert result.error_code is None


def test_decode_dtmf_from_audio_url_mock_failure() -> None:
    result = decode_dtmf_from_audio_url("mock-dtmf-fail://*246#")
    assert not result.success
    assert result.digits is None
    assert result.error_code == "DTMF_DECODE_FAILED"


@pytest.fixture
def _allow_example_com_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_getaddrinfo(
        host: str,
        port: int | str | None,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        del family, type, proto, flags
        if host == "example.com":
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("93.184.216.34", int(port or 443)),
                )
            ]
        raise socket.gaierror(f"unexpected host in test: {host}")

    monkeypatch.setattr("app.services.dtmf_audio.socket.getaddrinfo", fake_getaddrinfo)


@respx.mock
def test_decode_dtmf_from_audio_url_download_failure(
    _allow_example_com_dns: None,
) -> None:
    respx.get("https://example.com/recording.wav").mock(
        return_value=Response(404, text="missing")
    )

    result = decode_dtmf_from_audio_url("https://example.com/recording.wav")
    assert not result.success
    assert result.error_code == "DTMF_DECODE_FAILED"
    assert result.error_message is not None
    assert "Failed to download audio" in result.error_message


@pytest.mark.parametrize(
    "audio_url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/recording.wav",
        "http://localhost/recording.wav",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/recording.wav",
    ],
)
def test_validate_audio_download_url_rejects_unsafe_targets(audio_url: str) -> None:
    with pytest.raises(UnsafeAudioUrlError):
        validate_audio_download_url(audio_url)


def test_decode_dtmf_from_audio_url_rejects_unsafe_target() -> None:
    result = decode_dtmf_from_audio_url("http://127.0.0.1/recording.wav")
    assert not result.success
    assert result.error_code == "DTMF_DECODE_FAILED"
    assert result.error_message is not None
    assert "not allowed" in result.error_message


def test_decode_dtmf_from_audio_url_rejects_development_url_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.dtmf.settings.ENVIRONMENT", "production")

    result = decode_dtmf_from_audio_url("mock-dtmf://*246#")

    assert not result.success
    assert result.error_code == "DTMF_DECODE_FAILED"
    assert result.error_message is not None
    assert "Development DTMF URL shortcuts are disabled" in result.error_message


def test_format_dtmf_code_includes_checksum() -> None:
    assert format_dtmf_code(body=1) == "*11#"
    assert format_dtmf_code(body=12) == "*123#"


def test_validate_connexity_dtmf_code() -> None:
    assert validate_connexity_dtmf_code("*123#")
    assert not validate_connexity_dtmf_code("*125#")


def test_decode_dtmf_from_audio_bytes_clean_fixture() -> None:
    code = example_connexity_code(body=12)
    audio_bytes = build_dtmf_wav_bytes(code)

    result = decode_dtmf_from_audio_bytes(audio_bytes, content_type="audio/wav")

    assert result.success
    assert result.digits == code


def test_decode_dtmf_from_audio_bytes_noisy_fixture() -> None:
    code = example_connexity_code(body=12)
    audio_bytes = build_dtmf_wav_bytes(code, noise_amplitude=0.05, seed=7)

    result = decode_dtmf_from_audio_bytes(audio_bytes, content_type="audio/wav")

    assert result.success
    assert result.digits == code


def test_decode_dtmf_from_audio_bytes_missing_dtmf_fixture() -> None:
    audio_bytes = build_speech_like_wav_bytes()

    result = decode_dtmf_from_audio_bytes(audio_bytes, content_type="audio/wav")

    assert not result.success
    assert result.error_code == "DTMF_DECODE_FAILED"
    assert result.error_message is not None
    assert "No DTMF tones detected" in result.error_message


def test_decode_dtmf_from_audio_bytes_wrong_checksum_fixture() -> None:
    invalid_code = "*125#"
    audio_bytes = build_dtmf_wav_bytes(invalid_code)

    result = decode_dtmf_from_audio_bytes(audio_bytes, content_type="audio/wav")

    assert not result.success
    assert result.error_code == "DTMF_DECODE_FAILED"
    assert result.error_message is not None
    assert "no valid framed Connexity code" in result.error_message


def test_decode_dtmf_from_audio_bytes_repeated_tones_fixture() -> None:
    code = example_connexity_code(body=12)
    audio_bytes = build_dtmf_wav_bytes(f"{code}{code}")

    result = decode_dtmf_from_audio_bytes(audio_bytes, content_type="audio/wav")

    assert result.success
    assert result.digits == code


def test_decode_dtmf_from_audio_bytes_speech_only_false_positive_fixture() -> None:
    audio_bytes = build_speech_like_wav_bytes()

    result = decode_dtmf_from_audio_bytes(audio_bytes, content_type="audio/wav")

    assert not result.success
    assert result.digits is None


def test_decode_dtmf_from_audio_bytes_malformed_wav_fixture() -> None:
    result = decode_dtmf_from_audio_bytes(
        build_malformed_wav_bytes(),
        content_type="audio/wav",
    )

    assert not result.success
    assert result.error_code == "DTMF_DECODE_FAILED"
    assert result.error_message is not None
    assert "Failed to read WAV audio" in result.error_message


@respx.mock
def test_decode_dtmf_from_audio_url_real_wav_fixture(
    _allow_example_com_dns: None,
) -> None:
    code = example_connexity_code(body=12)
    audio_bytes = build_dtmf_wav_bytes(code)
    respx.get("https://example.com/recording.wav").mock(
        return_value=Response(
            200, content=audio_bytes, headers={"content-type": "audio/wav"}
        )
    )

    result = decode_dtmf_from_audio_url("https://example.com/recording.wav")

    assert result.success
    assert result.digits == code


@pytest.mark.parametrize(
    ("builder", "content_type"),
    [
        (build_dtmf_mp3_bytes, "audio/mpeg"),
        (build_dtmf_mulaw_wav_bytes, "audio/wav"),
        (build_dtmf_alaw_wav_bytes, "audio/wav"),
    ],
)
@pytestmark_codec
def test_decode_dtmf_from_audio_bytes_codec_fixtures(
    builder,
    content_type: str,
) -> None:
    code = example_connexity_code(body=12)
    audio_bytes = builder(code)

    result = decode_dtmf_from_audio_bytes(audio_bytes, content_type=content_type)

    assert result.success
    assert result.digits == code


def test_allocate_dtmf_code_increments(db) -> None:
    from app import crud
    from app.models import VoiceSimulationJobCreate
    from app.tests.utils.eval import (
        create_test_case_fixture,
        create_test_case_result_fixture,
        create_test_eval_config,
        create_test_run,
        eval_config_members,
    )

    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(test_case.id))
    run = create_test_run(
        db, agent_id=eval_config.agent_id, eval_config_id=eval_config.id
    )
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    first = allocate_dtmf_code(session=db)
    crud.create_voice_simulation_job(
        session=db,
        job_in=VoiceSimulationJobCreate(
            run_id=run.id,
            test_case_id=test_case.id,
            test_case_result_id=result.id,
            dtmf_code=first,
            agent_phone_number="+15551234567",
            stt_provider="deepgram",
            stt_model="nova-3",
            tts_provider="elevenlabs",
            tts_model="eleven_flash_v2_5",
            tts_voice_id="test-voice",
            max_call_duration_seconds=300,
        ),
    )
    second = allocate_dtmf_code(session=db)
    assert first != second
