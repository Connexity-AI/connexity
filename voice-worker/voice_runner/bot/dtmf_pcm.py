"""Connexity-compatible DTMF PCM (dual-tone ITU frequencies) for in-band signalling.

Pipecat's `load_dtmf_audio()` waveforms are not reliably detected by Connexity's decoder
(which uses the public PyPI `dtmf` package on 8 kHz mono PCM — same detector as backend
fixture tests).
"""

from __future__ import annotations

import math
import struct

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

# Matches backend decoder expectations (see `detect_dtmf_digits` MIN_*_BLOCKS and 205-sample blocks).
_TONE_DURATION_MS_DEFAULT = 120.0
_GAP_DURATION_MS_DEFAULT = 60.0


def pcm16_digit_tone(
    ch: str,
    *,
    sample_rate: int = 8000,
    duration_ms: float = _TONE_DURATION_MS_DEFAULT,
) -> bytes:
    frequencies = _DTMF_DIGIT_FREQS.get(ch)
    if frequencies is None:
        msg = f"Invalid DTMF character in framed code: {ch!r}"
        raise ValueError(msg)
    low_frequency, high_frequency = frequencies
    frame_count = max(1, int(sample_rate * (duration_ms / 1000)))
    chunk = bytearray()
    for frame_index in range(frame_count):
        time = frame_index / float(sample_rate)
        sample_float = 0.5 * (
            math.sin(2.0 * math.pi * low_frequency * time)
            + math.sin(2.0 * math.pi * high_frequency * time)
        )
        sample_i16 = max(-32768, min(32767, int(sample_float * 32767 * 0.8)))
        chunk.extend(struct.pack("<h", sample_i16))
    return bytes(chunk)


def pcm16_silence(*, sample_rate: int = 8000, duration_ms: float) -> bytes:
    samples = max(1, int(sample_rate * (duration_ms / 1000)))
    return b"\x00" * (samples * 2)


def concat_framed_dtmf_pcm16(
    framed_code: str,
    *,
    sample_rate: int = 8000,
    tone_ms: float = _TONE_DURATION_MS_DEFAULT,
    gap_ms: float = _GAP_DURATION_MS_DEFAULT,
) -> bytes:
    """Concatenate PCM16 mono tones (+inter-digit gaps) for a framed Connexity code."""
    out = bytearray()
    for index, ch in enumerate(framed_code):
        out.extend(pcm16_digit_tone(ch, sample_rate=sample_rate, duration_ms=tone_ms))
        if index < len(framed_code) - 1:
            out.extend(pcm16_silence(sample_rate=sample_rate, duration_ms=gap_ms))
    return bytes(out)
