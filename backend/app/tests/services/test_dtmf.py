import pytest

from app.services.dtmf import (
    allocate_dtmf_code,
    decode_dtmf_from_audio_url,
    format_dtmf_code,
)


@pytest.mark.parametrize(
    ("audio_url", "expected_digits"),
    [
        ("mock-dtmf://99124", "99124"),
        (
            "https://example.com/recordings/mock-dtmf/99124/call.wav",
            "99124",
        ),
        (
            "https://example.com/recording.wav?connexity_mock_dtmf=99103",
            "99103",
        ),
    ],
)
def test_decode_dtmf_from_audio_url_mock_success(
    audio_url: str,
    expected_digits: str,
) -> None:
    result = decode_dtmf_from_audio_url(audio_url)
    assert result.success
    assert result.digits == expected_digits
    assert result.error_code is None


def test_decode_dtmf_from_audio_url_mock_failure() -> None:
    result = decode_dtmf_from_audio_url("mock-dtmf-fail://99124")
    assert not result.success
    assert result.digits is None
    assert result.error_code == "DTMF_DECODE_FAILED"


def test_decode_dtmf_from_audio_url_unrecognized_url() -> None:
    result = decode_dtmf_from_audio_url("https://example.com/recording.wav")
    assert not result.success
    assert result.error_code == "DTMF_DECODE_FAILED"


def test_format_dtmf_code_includes_checksum() -> None:
    assert format_dtmf_code(body=1) == "9919"
    assert format_dtmf_code(body=12) == "99121"


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
        ),
    )
    second = allocate_dtmf_code(session=db)
    assert first != second
