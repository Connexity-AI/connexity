import pytest

from app.services.dtmf import decode_dtmf_from_audio_url


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
