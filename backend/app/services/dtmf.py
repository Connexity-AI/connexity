"""DTMF decoding from call recordings."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.config import settings
from app.models import VoiceSimulationJob
from app.services import dtmf_audio

_DEV_SCHEME_PREFIX = "mock-dtmf://"
_DEV_FAIL_SCHEME_PREFIX = "mock-dtmf-fail://"
_DEV_QUERY_KEY = "connexity_mock_dtmf"
_DEV_PATH_PATTERN = re.compile(r"/mock-dtmf/([^/]+)/")

FRAME_START = "*"
FRAME_END = "#"


def dtmf_checksum_digit(body: int) -> str:
    """Return the checksum digit for a Connexity DTMF code body."""
    digits = str(body)
    return str(sum(int(char) for char in digits if char.isdigit()) % 10)


def format_dtmf_code(*, body: int) -> str:
    """Build a framed Connexity DTMF code: *{body}{checksum}#."""
    checksum = dtmf_checksum_digit(body)
    return f"{FRAME_START}{body}{checksum}{FRAME_END}"


def parse_framed_dtmf_code(code: str) -> tuple[int, str] | None:
    """Parse a framed code into body and checksum, without validating checksum."""
    if not code.startswith(FRAME_START) or not code.endswith(FRAME_END):
        return None
    inner = code[1:-1]
    if len(inner) < 2:
        return None
    body_digits = inner[:-1]
    checksum = inner[-1]
    if not body_digits.isdigit() or not checksum.isdigit():
        return None
    return int(body_digits), checksum


def validate_connexity_dtmf_code(code: str) -> bool:
    """Return True when a framed code matches checksum rules."""
    parsed = parse_framed_dtmf_code(code)
    if parsed is None:
        return False
    body, checksum = parsed
    return checksum == dtmf_checksum_digit(body)


def _parse_dtmf_body(code: str) -> int | None:
    parsed = parse_framed_dtmf_code(code)
    if parsed is None:
        return None
    body, checksum = parsed
    if checksum != dtmf_checksum_digit(body):
        return None
    return body


def allocate_dtmf_code(*, session: Session) -> str:
    """Allocate the next incremental Connexity DTMF code for a new voice job."""
    statement = select(VoiceSimulationJob.dtmf_code).where(
        VoiceSimulationJob.dtmf_code.startswith(FRAME_START)
    )
    existing_codes = session.exec(statement).all()
    max_body = 0
    for code in existing_codes:
        parsed_body = _parse_dtmf_body(code)
        if parsed_body is not None:
            max_body = max(max_body, parsed_body)
    return format_dtmf_code(body=max_body + 1)


class DtmfDecodeResult(BaseModel):
    digits: str | None = Field(
        default=None,
        description="Decoded framed DTMF code when decoding succeeds",
    )
    error_code: str | None = Field(
        default=None,
        description="Machine-readable failure code when decoding fails",
    )
    error_message: str | None = Field(
        default=None,
        description="Human-readable failure reason when decoding fails",
    )

    @property
    def success(self) -> bool:
        return self.digits is not None and self.error_code is None


def decode_dtmf_from_audio_bytes(
    audio_bytes: bytes,
    *,
    content_type: str | None = None,
) -> DtmfDecodeResult:
    """Decode a framed Connexity DTMF code from raw audio bytes."""
    try:
        samples = dtmf_audio.normalize_audio_to_pcm(
            audio_bytes,
            content_type=content_type,
        )
    except dtmf_audio.AudioNormalizationError as exc:
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message=str(exc),
        )

    detected_digits = dtmf_audio.detect_dtmf_digits(samples)
    if not detected_digits:
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message="No DTMF tones detected in audio",
        )

    return _connexity_code_from_detected_digits(detected_digits)


def decode_dtmf_from_audio_url(audio_url: str) -> DtmfDecodeResult:
    """Decode a framed Connexity DTMF code from an audio URL."""
    development_result = _decode_development_dtmf_url(audio_url)
    if development_result is not None:
        return development_result

    try:
        audio_bytes, content_type = dtmf_audio.download_audio(audio_url)
    except httpx.HTTPError as exc:
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message=f"Failed to download audio: {exc}",
        )
    except dtmf_audio.UnsafeAudioUrlError as exc:
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message=str(exc),
        )
    except dtmf_audio.AudioDownloadError as exc:
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message=str(exc),
        )

    return decode_dtmf_from_audio_bytes(
        audio_bytes,
        content_type=content_type,
    )


def development_dtmf_urls_enabled() -> bool:
    """Return True when development-only DTMF URL shortcuts are allowed."""
    return settings.ENVIRONMENT == "local"


def _decode_development_dtmf_url(audio_url: str) -> DtmfDecodeResult | None:
    if not _looks_like_development_dtmf_url(audio_url):
        return None

    if not development_dtmf_urls_enabled():
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message=(
                "Development DTMF URL shortcuts are disabled outside local environment"
            ),
        )

    if audio_url.startswith(_DEV_FAIL_SCHEME_PREFIX):
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message="Development DTMF decoder configured to fail for this URL",
        )

    if audio_url.startswith(_DEV_SCHEME_PREFIX):
        code = unquote(audio_url.removeprefix(_DEV_SCHEME_PREFIX).strip("/"))
        if validate_connexity_dtmf_code(code):
            return DtmfDecodeResult(digits=code)
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message=(
                "Development DTMF URL must contain a framed Connexity code "
                "after mock-dtmf://"
            ),
        )

    parsed = urlparse(audio_url)
    query_values = parse_qs(parsed.query).get(_DEV_QUERY_KEY)
    if query_values:
        code = unquote(query_values[0])
        if validate_connexity_dtmf_code(code):
            return DtmfDecodeResult(digits=code)
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message=f"Query param {_DEV_QUERY_KEY} must contain a framed code",
        )

    path_match = _DEV_PATH_PATTERN.search(parsed.path)
    if path_match:
        code = unquote(path_match.group(1))
        if validate_connexity_dtmf_code(code):
            return DtmfDecodeResult(digits=code)
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message="Development DTMF path segment must contain a framed code",
        )

    return None


def _looks_like_development_dtmf_url(audio_url: str) -> bool:
    if audio_url.startswith(_DEV_FAIL_SCHEME_PREFIX):
        return True
    if audio_url.startswith(_DEV_SCHEME_PREFIX):
        return True

    parsed = urlparse(audio_url)
    if parse_qs(parsed.query).get(_DEV_QUERY_KEY):
        return True
    return _DEV_PATH_PATTERN.search(parsed.path) is not None


def _connexity_code_from_detected_digits(detected_digits: str) -> DtmfDecodeResult:
    framed_codes = _extract_framed_codes(detected_digits)
    unique_codes = list(dict.fromkeys(framed_codes))
    if len(unique_codes) == 1:
        return DtmfDecodeResult(digits=unique_codes[0])
    if len(unique_codes) > 1:
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message="Ambiguous DTMF detection: multiple valid framed codes found",
        )
    return DtmfDecodeResult(
        error_code="DTMF_DECODE_FAILED",
        error_message=(
            "DTMF tones detected but no valid framed Connexity code "
            f"({FRAME_START}{{body}}{{checksum}}{FRAME_END}) was found"
        ),
    )


def _extract_framed_codes(detected_digits: str) -> list[str]:
    framed_codes: list[str] = []
    search_start = 0
    while True:
        start_index = detected_digits.find(FRAME_START, search_start)
        if start_index == -1:
            break
        end_index = detected_digits.find(FRAME_END, start_index + 1)
        if end_index == -1:
            break
        candidate = detected_digits[start_index : end_index + 1]
        if validate_connexity_dtmf_code(candidate):
            framed_codes.append(candidate)
        search_start = end_index + 1
    return framed_codes
