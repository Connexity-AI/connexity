"""Emit in-band PCM DTMF audio after the callee's first finalized utterance."""

from __future__ import annotations

from pipecat.frames.frames import OutputAudioRawFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from voice_runner.bot.dtmf_pcm import pcm16_digit_tone, pcm16_silence


def keypad_for_dtmf_char(ch: str) -> str:
    """Validate a framed Connexity DTMF digit and return it (backward-compatible helper)."""
    allowed = frozenset("0123456789*#")
    if ch not in allowed:
        msg = f"Invalid DTMF character in code: {ch!r}"
        raise ValueError(msg)
    return ch


class PersonaFirstReplyDtmfProcessor(FrameProcessor):
    """Play Connexity framed DTMF digits once, before the first final transcript continues."""

    def __init__(self, *, dtmf_code: str, sample_rate: int = 8000, **kwargs) -> None:
        super().__init__(**kwargs)
        self._dtmf_code = dtmf_code
        self._sample_rate = sample_rate
        self._emitted = False

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if (
            isinstance(frame, TranscriptionFrame)
            and frame.finalized
            and not self._emitted
        ):
            self._emitted = True
            code = self._dtmf_code
            for index, ch in enumerate(code):
                keypad_for_dtmf_char(ch)
                pcm = pcm16_digit_tone(ch, sample_rate=self._sample_rate)
                await self.push_frame(
                    OutputAudioRawFrame(
                        audio=pcm,
                        sample_rate=self._sample_rate,
                        num_channels=1,
                    ),
                    direction,
                )
                if index < len(code) - 1:
                    gap = pcm16_silence(
                        sample_rate=self._sample_rate,
                        duration_ms=60.0,
                    )
                    await self.push_frame(
                        OutputAudioRawFrame(
                            audio=gap,
                            sample_rate=self._sample_rate,
                            num_channels=1,
                        ),
                        direction,
                    )

        await self.push_frame(frame, direction)


__all__ = ["PersonaFirstReplyDtmfProcessor", "keypad_for_dtmf_char"]
