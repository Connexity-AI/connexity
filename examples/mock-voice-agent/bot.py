"""Pipecat inbound Twilio pipeline for the Connexity mock voice agent."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import WebSocket
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transcriptions.language import Language
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from connexity import save_call_recording_wav
from settings import Settings
from tools import lookup_order

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful customer support voice agent for Connexity.

You are on a phone call. Keep replies short, natural, and easy to speak aloud.
When a caller mentions an order id (for example ORD-12345), use lookup_order before answering.
Do not invent order details. Ask clarifying questions when the caller is vague.
Stay professional and empathetic."""


async def _lookup_order_handler(params: FunctionCallParams) -> None:
    order_id = str(params.arguments.get("order_id", ""))
    result = lookup_order(order_id)
    await params.result_callback(result)


async def run_inbound_voice_call(
    websocket: WebSocket,
    *,
    settings: Settings,
    on_call_complete: Callable[..., Awaitable[None]] | None = None,
) -> None:
    """Run one inbound Twilio Media Stream call through Pipecat.

    ``on_call_complete`` is the Connexity integration hook — see ``main.py``.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        msg = "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set"
        raise RuntimeError(msg)
    if not settings.DEEPGRAM_API_KEY:
        msg = "DEEPGRAM_API_KEY is required for speech-to-text"
        raise RuntimeError(msg)
    if not settings.OPENAI_API_KEY:
        msg = "OPENAI_API_KEY is required for the LLM"
        raise RuntimeError(msg)
    if not settings.ELEVENLABS_API_KEY:
        msg = "ELEVENLABS_API_KEY is required for text-to-speech"
        raise RuntimeError(msg)

    _transport_name, call_data = await parse_telephony_websocket(websocket)
    call_sid = str(call_data["call_id"])
    stream_sid = str(call_data["stream_id"])
    recording_path = settings.recordings_dir / f"{call_sid}.wav"

    vad = SileroVADAnalyzer()
    serializer = TwilioFrameSerializer(
        stream_sid,
        call_sid=call_sid,
        account_sid=settings.TWILIO_ACCOUNT_SID,
        auth_token=settings.TWILIO_AUTH_TOKEN,
        params=TwilioFrameSerializer.InputParams(
            sample_rate=8000,
            twilio_sample_rate=8000,
        ),
    )

    transport = FastAPIWebsocketTransport(
        websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=vad,
            serializer=serializer,
        ),
    )

    lookup_order_schema = FunctionSchema(
        name="lookup_order",
        description="Fetch order details by order id (for example ORD-12345).",
        properties={
            "order_id": {
                "type": "string",
                "description": "Order identifier",
            }
        },
        required=["order_id"],
    )
    tools = ToolsSchema(standard_tools=[lookup_order_schema])

    llm = OpenAILLMService(
        api_key=settings.OPENAI_API_KEY,
        settings=OpenAILLMService.Settings(
            model=settings.MOCK_VOICE_LLM_MODEL,
            temperature=0.2,
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    llm.register_function("lookup_order", _lookup_order_handler)

    stt = DeepgramSTTService(
        api_key=settings.DEEPGRAM_API_KEY,
        sample_rate=8000,
        encoding="linear16",
        channels=1,
        settings=DeepgramSTTService.Settings(
            model=settings.MOCK_VOICE_DEEPGRAM_STT_MODEL,
            language=Language.EN,
            interim_results=True,
        ),
    )

    tts = ElevenLabsTTSService(
        api_key=settings.ELEVENLABS_API_KEY,
        settings=ElevenLabsTTSService.Settings(
            model=settings.MOCK_VOICE_ELEVENLABS_TTS_MODEL,
            voice=settings.MOCK_VOICE_ELEVENLABS_VOICE_ID,
        ),
        sample_rate=8000,
    )

    # LLMContext accumulates OpenAI-format messages Connexity expects at submission time.
    context = LLMContext(tools=tools)
    user_agg_params = LLMUserAggregatorParams(
        vad_analyzer=cast(VADAnalyzer, vad),
    )
    aggregation = LLMContextAggregatorPair(context, user_params=user_agg_params)

    # Merged call audio — must preserve Connexity DTMF tones for audio_url decoding.
    audiobuffer = AudioBufferProcessor()

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            aggregation.user(),
            llm,
            tts,
            transport.output(),
            audiobuffer,
            aggregation.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            allow_interruptions=True,
        ),
    )

    saved_audio: dict[str, bytes | None] = {"payload": None}
    saved_meta: dict[str, int] = {"sample_rate": 8000, "num_channels": 1}

    @transport.event_handler("on_client_connected")
    async def _on_connected(
        _transport: FastAPIWebsocketTransport, _ws: WebSocket
    ) -> None:
        await audiobuffer.start_recording()
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def _on_disconnected(
        _transport: FastAPIWebsocketTransport, _ws: WebSocket
    ) -> None:
        await audiobuffer.stop_recording()
        await task.cancel()

    @audiobuffer.event_handler("on_audio_data")
    async def _on_audio_data(
        _buffer: AudioBufferProcessor,
        audio: bytes,
        sample_rate: int,
        num_channels: int,
    ) -> None:
        saved_audio["payload"] = audio
        saved_meta["sample_rate"] = sample_rate
        saved_meta["num_channels"] = num_channels

    runner = PipelineRunner(handle_sigint=False, handle_sigterm=False)
    logger.info(
        "Starting mock voice agent call_sid=%s stream_sid=%s", call_sid, stream_sid
    )

    try:
        await runner.run(task)
    finally:
        audio = saved_audio["payload"]
        if audio:
            await save_call_recording_wav(
                audio=audio,
                sample_rate=saved_meta["sample_rate"],
                num_channels=saved_meta["num_channels"],
                path=recording_path,
            )
            logger.info("Saved call recording to %s", recording_path)

        # CONNEXITY: hand off recording + LLMContext when the call ends.
        if on_call_complete is not None and audio:
            await on_call_complete(
                call_sid=call_sid,
                recording_path=recording_path,
                context=context,
            )
