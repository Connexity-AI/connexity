"""Audio download, normalization, and DTMF tone detection."""

from __future__ import annotations

import io
import ipaddress
import shutil
import socket
import struct
import subprocess
import wave
from typing import Final
from urllib.parse import urlparse

import httpx
from dtmf import detect

from app.core.config import settings

TARGET_SAMPLE_RATE: Final[int] = 8000
MIN_TONE_BLOCKS: Final[int] = 2
MIN_GAP_BLOCKS: Final[int] = 2
_BLOCK_SIZE: Final[int] = 205
_SILENCE_EPSILON: Final[float] = 1e-8


class AudioDownloadError(Exception):
    """Raised when audio cannot be downloaded from a URL."""


class AudioNormalizationError(Exception):
    """Raised when audio bytes cannot be converted to mono PCM."""


class UnsafeAudioUrlError(AudioDownloadError):
    """Raised when an audio URL points to an unsafe destination."""


def validate_audio_download_url(url: str) -> None:
    """Reject URLs that could target internal or disallowed destinations."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        msg = f"Unsupported audio URL scheme: {parsed.scheme or 'missing'}"
        raise UnsafeAudioUrlError(msg)

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeAudioUrlError("Audio URL must include a hostname")

    if _is_unsafe_host(hostname):
        raise UnsafeAudioUrlError(f"Audio URL host is not allowed: {hostname}")

    try:
        address_infos = socket.getaddrinfo(
            hostname,
            parsed.port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        msg = f"Audio URL hostname could not be resolved: {hostname}"
        raise UnsafeAudioUrlError(msg) from exc

    for family, _, _, _, sockaddr in address_infos:
        del family
        address = str(sockaddr[0])
        if _is_unsafe_ip(address):
            raise UnsafeAudioUrlError(
                f"Audio URL resolves to a disallowed address: {address}"
            )


def download_audio(url: str) -> tuple[bytes, str | None]:
    """Download audio bytes from a URL with size and timeout limits."""
    validate_audio_download_url(url)
    timeout = httpx.Timeout(settings.DTMF_AUDIO_DOWNLOAD_TIMEOUT_SECONDS)
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type")
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > settings.DTMF_AUDIO_MAX_BYTES:
                    msg = (
                        f"Audio exceeds maximum size of "
                        f"{settings.DTMF_AUDIO_MAX_BYTES} bytes"
                    )
                    raise AudioDownloadError(msg)
                chunks.append(chunk)
    return b"".join(chunks), content_type


def normalize_audio_to_pcm(
    audio_bytes: bytes,
    *,
    content_type: str | None = None,
) -> list[float]:
    """Convert audio bytes to mono floating-point PCM at 8 kHz."""
    if shutil.which("ffmpeg") is not None:
        try:
            return _normalize_with_ffmpeg(audio_bytes)
        except AudioNormalizationError:
            if not _looks_like_wav(audio_bytes, content_type):
                raise
    elif not _looks_like_wav(audio_bytes, content_type):
        msg = (
            "Unsupported audio format. Install ffmpeg for automatic conversion "
            "or provide WAV/RIFF audio."
        )
        raise AudioNormalizationError(msg)

    try:
        samples, sample_rate = _read_wav_pcm(audio_bytes)
    except (EOFError, struct.error, wave.Error, ValueError) as exc:
        msg = f"Failed to read WAV audio: {exc}"
        raise AudioNormalizationError(msg) from exc

    mono = _to_mono(samples)
    return _resample(mono, sample_rate, TARGET_SAMPLE_RATE)


def detect_dtmf_digits(samples: list[float]) -> str:
    """Detect a DTMF digit sequence from mono PCM samples."""
    if not samples:
        return ""

    detected_digits: list[str] = []
    current_tone: str | None = None
    tone_blocks = 0
    gap_blocks = 0
    sample_rate = float(TARGET_SAMPLE_RATE)
    detection_samples = _prepare_samples_for_detection(samples)

    for result in detect(detection_samples, sample_rate):
        if result.tone is None:
            gap_blocks += 1
            if current_tone is not None and gap_blocks >= MIN_GAP_BLOCKS:
                if tone_blocks >= MIN_TONE_BLOCKS:
                    detected_digits.append(current_tone)
                current_tone = None
                tone_blocks = 0
            continue

        gap_blocks = 0
        tone_char = str(result.tone)
        if tone_char == current_tone:
            tone_blocks += 1
            continue

        if current_tone is not None and tone_blocks >= MIN_TONE_BLOCKS:
            detected_digits.append(current_tone)
        current_tone = tone_char
        tone_blocks = 1

    if current_tone is not None and tone_blocks >= MIN_TONE_BLOCKS:
        detected_digits.append(current_tone)

    return "".join(detected_digits)


def _prepare_samples_for_detection(samples: list[float]) -> list[float]:
    """Avoid all-zero blocks that crash the public dtmf.detect() implementation."""
    prepared: list[float] = []
    for index in range(0, len(samples), _BLOCK_SIZE):
        block = samples[index : index + _BLOCK_SIZE]
        if not block:
            continue
        if sum(abs(sample) for sample in block) == 0:
            prepared.extend([_SILENCE_EPSILON] * len(block))
        else:
            prepared.extend(block)
    return prepared


def _is_unsafe_host(hostname: str) -> bool:
    lowered = hostname.lower()
    if lowered in {"localhost", "metadata.google.internal"}:
        return True
    if lowered.endswith(".local") or lowered.endswith(".internal"):
        return True
    try:
        return _is_unsafe_ip(hostname)
    except ValueError:
        return False


def _is_unsafe_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
    )


def _looks_like_wav(audio_bytes: bytes, content_type: str | None) -> bool:
    if audio_bytes.startswith(b"RIFF"):
        return True
    return bool(content_type and "wav" in content_type.lower())


def _normalize_with_ffmpeg(audio_bytes: bytes) -> list[float]:
    process = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            "pipe:0",
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            str(TARGET_SAMPLE_RATE),
            "pipe:1",
        ],
        input=audio_bytes,
        capture_output=True,
        check=False,
        timeout=settings.DTMF_FFMPEG_TIMEOUT_SECONDS,
    )
    if process.returncode != 0 or not process.stdout:
        stderr = process.stderr.decode("utf-8", errors="replace").strip()
        msg = f"ffmpeg failed to normalize audio: {stderr or 'unknown error'}"
        raise AudioNormalizationError(msg)
    return _decode_s16le_pcm(process.stdout)


def _decode_s16le_pcm(raw_frames: bytes) -> list[float]:
    if len(raw_frames) % 2 != 0:
        msg = "Invalid PCM audio: odd number of bytes"
        raise AudioNormalizationError(msg)
    if not raw_frames:
        return []
    sample_count = len(raw_frames) // 2
    raw_values = struct.unpack(f"{sample_count}h", raw_frames)
    return [value / 32768.0 for value in raw_values]


def _read_wav_pcm(audio_bytes: bytes) -> tuple[list[list[float]], int]:
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        channel_count = wav_file.getnchannels()
        frame_count = wav_file.getnframes()
        raw_frames = wav_file.readframes(frame_count)

    if sample_width not in {1, 2, 4}:
        msg = f"Unsupported WAV sample width: {sample_width}"
        raise AudioNormalizationError(msg)

    samples_per_channel = _decode_pcm_frames(
        raw_frames,
        sample_width=sample_width,
        frame_count=frame_count,
        channel_count=channel_count,
    )
    return samples_per_channel, sample_rate


def _decode_pcm_frames(
    raw_frames: bytes,
    *,
    sample_width: int,
    frame_count: int,
    channel_count: int,
) -> list[list[float]]:
    if sample_width == 1:
        unpack_format = f"{frame_count * channel_count}B"
        scale = 127.0
        offset = 128.0
        raw_values = struct.unpack(unpack_format, raw_frames)
        floats = [(value - offset) / scale for value in raw_values]
    elif sample_width == 2:
        unpack_format = f"{frame_count * channel_count}h"
        scale = 32768.0
        raw_values = struct.unpack(unpack_format, raw_frames)
        floats = [value / scale for value in raw_values]
    else:
        unpack_format = f"{frame_count * channel_count}i"
        scale = 2147483648.0
        raw_values = struct.unpack(unpack_format, raw_frames)
        floats = [value / scale for value in raw_values]

    if channel_count == 1:
        return [floats]

    channels: list[list[float]] = [[] for _ in range(channel_count)]
    for index, value in enumerate(floats):
        channels[index % channel_count].append(value)
    return channels


def _to_mono(channels: list[list[float]]) -> list[float]:
    if len(channels) == 1:
        return channels[0]
    frame_count = min(len(channel) for channel in channels)
    return [
        sum(channel[index] for channel in channels) / len(channels)
        for index in range(frame_count)
    ]


def _resample(samples: list[float], from_rate: int, to_rate: int) -> list[float]:
    if from_rate == to_rate or not samples:
        return samples
    output_length = max(1, int(len(samples) * to_rate / from_rate))
    resampled: list[float] = []
    for output_index in range(output_length):
        source_position = output_index * from_rate / to_rate
        left_index = int(source_position)
        right_index = min(left_index + 1, len(samples) - 1)
        blend = source_position - left_index
        value = samples[left_index] * (1.0 - blend) + samples[right_index] * blend
        resampled.append(value)
    return resampled
