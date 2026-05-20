"""DTMF decoding from call recordings.

The mock decoder extracts digits from special URL patterns for tests and local
development. Real audio decoding is implemented in a later build step.
"""

import re
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models import VoiceSimulationJob

_MOCK_SCHEME_PREFIX = "mock-dtmf://"
_MOCK_FAIL_SCHEME_PREFIX = "mock-dtmf-fail://"
_MOCK_QUERY_KEY = "connexity_mock_dtmf"
_MOCK_PATH_PATTERN = re.compile(r"/mock-dtmf/(\d+)/")

DEFAULT_DTMF_PREFIX = "99"


def dtmf_checksum_digit(prefix: str, body: int) -> str:
    """Return the checksum digit for a Connexity DTMF code body."""
    digits = f"{prefix}{body}"
    return str(sum(int(char) for char in digits if char.isdigit()) % 10)


def format_dtmf_code(*, prefix: str = DEFAULT_DTMF_PREFIX, body: int) -> str:
    """Build a Connexity DTMF code from prefix, incremental body, and checksum."""
    checksum = dtmf_checksum_digit(prefix, body)
    return f"{prefix}{body}{checksum}"


def _parse_dtmf_body(code: str, *, prefix: str = DEFAULT_DTMF_PREFIX) -> int | None:
    if not code.startswith(prefix) or len(code) <= len(prefix) + 1:
        return None
    body_digits = code[len(prefix) : -1]
    if not body_digits.isdigit():
        return None
    return int(body_digits)


def allocate_dtmf_code(
    *,
    session: Session,
    prefix: str = DEFAULT_DTMF_PREFIX,
) -> str:
    """Allocate the next incremental Connexity DTMF code for a new voice job."""
    statement = select(VoiceSimulationJob.dtmf_code).where(
        VoiceSimulationJob.dtmf_code.startswith(prefix)
    )
    existing_codes = session.exec(statement).all()
    max_body = 0
    for code in existing_codes:
        parsed_body = _parse_dtmf_body(code, prefix=prefix)
        if parsed_body is not None:
            max_body = max(max_body, parsed_body)
    return format_dtmf_code(prefix=prefix, body=max_body + 1)


class DtmfDecodeResult(BaseModel):
    digits: str | None = Field(
        default=None,
        description="Decoded DTMF digit sequence when decoding succeeds",
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


def decode_dtmf_from_audio_url(audio_url: str) -> DtmfDecodeResult:
    """Decode DTMF digits from an audio URL using the mock decoder."""
    if audio_url.startswith(_MOCK_FAIL_SCHEME_PREFIX):
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message="Mock DTMF decoder configured to fail for this URL",
        )

    if audio_url.startswith(_MOCK_SCHEME_PREFIX):
        digits = audio_url.removeprefix(_MOCK_SCHEME_PREFIX).strip("/")
        if digits.isdigit():
            return DtmfDecodeResult(digits=digits)
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message="Mock DTMF URL must contain digits after mock-dtmf://",
        )

    parsed = urlparse(audio_url)
    query_values = parse_qs(parsed.query).get(_MOCK_QUERY_KEY)
    if query_values:
        digits = query_values[0]
        if digits.isdigit():
            return DtmfDecodeResult(digits=digits)
        return DtmfDecodeResult(
            error_code="DTMF_DECODE_FAILED",
            error_message=f"Query param {_MOCK_QUERY_KEY} must contain digits",
        )

    path_match = _MOCK_PATH_PATTERN.search(parsed.path)
    if path_match:
        return DtmfDecodeResult(digits=path_match.group(1))

    return DtmfDecodeResult(
        error_code="DTMF_DECODE_FAILED",
        error_message=(
            "No DTMF digits found in audio URL. For local development use "
            "mock-dtmf://<code>, a /mock-dtmf/<code>/ path segment, or "
            f"?{_MOCK_QUERY_KEY}=<code>."
        ),
    )
