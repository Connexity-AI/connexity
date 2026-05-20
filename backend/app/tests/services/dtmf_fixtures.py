"""Synthetic DTMF audio fixtures for decoder tests."""

from __future__ import annotations

import io
import math
import random
import shutil
import struct
import subprocess
import wave

from app.services.dtmf import format_dtmf_code

_DTMF_DIGIT_FREQS: dict[str, tuple[float, float]] = {
    "1": (697.0, 1209.0),
    "2": (697.0, 1336.0),
    "3": (697.0, 1477.0),
    "4": (770.0, 1209.0),
    "5": (770.0, 1336.0),
    "6": (770.0, 1477.0),
    "7": (852.0, 1209.0),
    "8": (852.0, 1336.0),
    "9": (852.0, 1477.0),
    "0": (941.0, 1336.0),
    "*": (941.0, 1209.0),
    "#": (941.0, 1477.0),
}


def build_dtmf_wav_bytes(
    code: str,
    *,
    sample_rate: int = 8000,
    tone_ms: int = 120,
    gap_ms: int = 60,
    leading_silence_ms: int = 40,
    trailing_silence_ms: int = 40,
    noise_amplitude: float = 0.0,
    seed: int | None = None,
) -> bytes:
    """Build a mono WAV file containing a DTMF digit sequence."""
    samples = build_dtmf_samples(
        code,
        sample_rate=sample_rate,
        tone_ms=tone_ms,
        gap_ms=gap_ms,
        leading_silence_ms=leading_silence_ms,
        trailing_silence_ms=trailing_silence_ms,
        noise_amplitude=noise_amplitude,
        seed=seed,
    )
    return samples_to_wav_bytes(samples, sample_rate=sample_rate)


def build_dtmf_samples(
    code: str,
    *,
    sample_rate: int = 8000,
    tone_ms: int = 120,
    gap_ms: int = 60,
    leading_silence_ms: int = 40,
    trailing_silence_ms: int = 40,
    noise_amplitude: float = 0.0,
    seed: int | None = None,
) -> list[float]:
    """Build mono PCM samples for a DTMF digit sequence."""
    rng = random.Random(seed)
    samples: list[float] = [0.0] * int(sample_rate * leading_silence_ms / 1000)
    gap_samples = int(sample_rate * gap_ms / 1000)

    for index, digit in enumerate(code):
        samples.extend(
            _generate_digit_samples(
                digit,
                sample_rate=sample_rate,
                duration_ms=tone_ms,
            )
        )
        if index < len(code) - 1:
            samples.extend([0.0] * gap_samples)

    samples.extend([0.0] * int(sample_rate * trailing_silence_ms / 1000))
    if noise_amplitude > 0:
        samples = [
            sample + rng.uniform(-noise_amplitude, noise_amplitude)
            for sample in samples
        ]
    return samples


def build_speech_like_wav_bytes(
    *, sample_rate: int = 8000, duration_ms: int = 800
) -> bytes:
    """Build a speech-like sine mixture without DTMF row/column pairs."""
    samples: list[float] = []
    frame_count = int(sample_rate * duration_ms / 1000)
    frequencies = (300.0, 450.0, 620.0, 880.0)
    for frame_index in range(frame_count):
        time = frame_index / sample_rate
        value = sum(
            math.sin(2.0 * math.pi * frequency * time) for frequency in frequencies
        )
        samples.append(0.15 * value / len(frequencies))
    return samples_to_wav_bytes(samples, sample_rate=sample_rate)


def build_malformed_wav_bytes() -> bytes:
    """Return truncated WAV bytes for normalization failure tests."""
    return b"RIFF\x24\x00\x00\x00WAVEfmt "


def ffmpeg_available() -> bool:
    """Return True when ffmpeg is available for codec fixture generation."""
    return shutil.which("ffmpeg") is not None


def transcode_wav_with_ffmpeg(
    wav_bytes: bytes,
    *,
    output_format: str,
    codec: str | None = None,
) -> bytes:
    """Transcode fixture WAV bytes to another audio format using ffmpeg."""
    if not ffmpeg_available():
        msg = "ffmpeg is required to build codec fixtures"
        raise RuntimeError(msg)

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-i",
        "pipe:0",
        "-f",
        output_format,
    ]
    if codec is not None:
        command.extend(["-acodec", codec])
    command.append("pipe:1")

    process = subprocess.run(
        command,
        input=wav_bytes,
        capture_output=True,
        check=False,
        timeout=30.0,
    )
    if process.returncode != 0 or not process.stdout:
        stderr = process.stderr.decode("utf-8", errors="replace").strip()
        msg = f"ffmpeg fixture transcode failed: {stderr or 'unknown error'}"
        raise RuntimeError(msg)
    return process.stdout


def build_dtmf_mp3_bytes(code: str) -> bytes:
    """Build an MP3 fixture containing a DTMF digit sequence."""
    return transcode_wav_with_ffmpeg(
        build_dtmf_wav_bytes(code),
        output_format="mp3",
        codec="libmp3lame",
    )


def build_dtmf_mulaw_wav_bytes(code: str) -> bytes:
    """Build a mu-law WAV fixture containing a DTMF digit sequence."""
    return transcode_wav_with_ffmpeg(
        build_dtmf_wav_bytes(code),
        output_format="wav",
        codec="pcm_mulaw",
    )


def build_dtmf_alaw_wav_bytes(code: str) -> bytes:
    """Build an A-law WAV fixture containing a DTMF digit sequence."""
    return transcode_wav_with_ffmpeg(
        build_dtmf_wav_bytes(code),
        output_format="wav",
        codec="pcm_alaw",
    )


def samples_to_wav_bytes(samples: list[float], *, sample_rate: int = 8000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = b"".join(
            struct.pack(
                "<h",
                max(-32768, min(32767, int(sample * 32767 * 0.8))),
            )
            for sample in samples
        )
        wav_file.writeframes(frames)
    return buffer.getvalue()


def example_connexity_code(*, body: int = 12) -> str:
    """Return a valid framed Connexity code for fixture generation."""
    return format_dtmf_code(body=body)


def _generate_digit_samples(
    digit: str,
    *,
    sample_rate: int,
    duration_ms: int,
) -> list[float]:
    frequencies = _DTMF_DIGIT_FREQS.get(digit)
    if frequencies is None:
        msg = f"Unsupported DTMF fixture digit: {digit!r}"
        raise ValueError(msg)
    low_frequency, high_frequency = frequencies
    frame_count = int(sample_rate * duration_ms / 1000)
    samples: list[float] = []
    for frame_index in range(frame_count):
        time = frame_index / sample_rate
        sample = 0.5 * (
            math.sin(2.0 * math.pi * low_frequency * time)
            + math.sin(2.0 * math.pi * high_frequency * time)
        )
        samples.append(sample)
    return samples
