"""Connexity voice integration for examples/mock-voice-agent/.

=============================================================================
INTEGRATION GUIDE — what you must implement for Connexity voice evals
=============================================================================

When adapting this example for your own voice agent, Connexity requires exactly
three things after each eval call ends:

1. **Public recording URL (`audio_url`)**
   - Build with :func:`recording_public_url`.
   - Must be reachable by the Connexity backend over http/https.
   - Must include Connexity's in-band DTMF tones from the caller leg.
   - Serve the file from your app (see ``GET /recordings/{filename}`` in
     ``main.py``), Twilio call recording, S3, etc.

2. **Agent-side transcript (`messages`)**
   - Build with :func:`messages_for_submission` from your conversation state.
   - Pipecat's ``LLMContext.get_messages()`` is already OpenAI-format; we only
     drop ``system`` / developer prompts Connexity does not judge.
   - Include ``assistant`` / ``user`` / ``tool`` turns and any ``tool_calls``.

3. **Result submission**
   - Call :func:`submit_voice_result` (or :func:`submit_call_to_connexity`) when
     the call ends and both artifacts above are ready.
   - Auth: ``Authorization: Bearer <jwt>`` from Connexity login.
   - Endpoint: ``POST /api/v1/voice-simulations/results``
   - Do **not** send ``test_case_id``, ``run_id``, or DTMF code — Connexity
     routes by decoding DTMF from ``audio_url``.

Everything else in this repo (Pipecat pipeline, Twilio webhooks, STT/TTS, tools)
is your agent implementation, not part of the Connexity contract.

See docs/voice-agent-contract.md for the full specification.
"""

from __future__ import annotations

import io
import logging
import wave
from pathlib import Path
from typing import Any, cast

import aiofiles
import httpx
from pipecat.processors.aggregators.llm_context import LLMContext

from settings import Settings

logger = logging.getLogger(__name__)

# Roles Connexity judges from agent-side voice submissions (see voice-agent-contract.md).
_SUBMISSION_ROLES = frozenset({"user", "assistant", "tool"})


def recording_public_url(settings: Settings, call_sid: str) -> str:
    """Public ``audio_url`` submitted to Connexity for this call.

    Replace this if you host recordings on S3, Twilio Recording URLs, etc.
    The URL must include Connexity's in-band DTMF tones.
    """
    base = settings.MOCK_VOICE_AGENT_PUBLIC_BASE_URL.strip().rstrip("/")
    return f"{base}/recordings/{call_sid}.wav"


def messages_for_submission(context: LLMContext) -> list[dict[str, Any]]:
    """OpenAI-format messages for ``POST /voice-simulations/results``.

    Pipecat's ``LLMContext`` stores messages in OpenAI chat shape already.
    Connexity only needs conversational turns — skip system/developer prompts.
    """
    messages = [
        message
        for message in context.get_messages()
        if isinstance(message, dict) and message.get("role") in _SUBMISSION_ROLES
    ]
    if not messages:
        msg = "No user/assistant/tool messages captured during the call"
        raise ValueError(msg)
    return cast(list[dict[str, Any]], messages)


async def save_call_recording_wav(
    *,
    audio: bytes,
    sample_rate: int,
    num_channels: int,
    path: Path,
) -> None:
    """Write merged call audio to disk so it can be served at ``audio_url``.

    Replace this if you upload to object storage or use Twilio Recording instead.
    """
    if not audio:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wf:
            wf.setsampwidth(2)
            wf.setnchannels(num_channels)
            wf.setframerate(sample_rate)
            wf.writeframes(audio)
        async with aiofiles.open(path, "wb") as file:
            await file.write(buffer.getvalue())


async def submit_voice_result(
    *,
    settings: Settings,
    audio_url: str,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """POST ``{audio_url, messages}`` to Connexity after a voice eval call.

    This is the core Connexity integration call. Wire it from your call-ended
    handler (see ``main.py`` → ``submit_call_to_connexity``).
    """
    token = settings.CONNEXITY_API_TOKEN.strip()
    if not token:
        msg = "CONNEXITY_API_TOKEN is required to submit voice results"
        raise ValueError(msg)

    base = settings.CONNEXITY_API_URL.strip().rstrip("/")
    url = f"{base}/api/v1/voice-simulations/results"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"audio_url": audio_url, "messages": messages}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()
        logger.info(
            "Submitted voice result job=%s status=%s",
            body.get("id"),
            body.get("status"),
        )
        return body


async def submit_call_to_connexity(
    *,
    settings: Settings,
    call_sid: str,
    recording_path: Path,
    context: LLMContext,
) -> None:
    """End-to-end Connexity submission for one completed call.

    Called from ``main.py`` when the Pipecat pipeline finishes. Combines the
    three integration steps: recording URL, transcript export, and result POST.
    """
    if not recording_path.is_file():
        logger.warning(
            "Recording missing for call_sid=%s; skipping Connexity submission",
            call_sid,
        )
        return

    audio_url = recording_public_url(settings, call_sid)
    messages = messages_for_submission(context)
    await submit_voice_result(
        settings=settings,
        audio_url=audio_url,
        messages=messages,
    )
