"""Assemble Pipecat 1.2.1 Twilio websocket pipeline for a claimed voice job."""

from __future__ import annotations

import logging
from typing import Any, cast

from app.core.config import settings as connexity_settings
from app.models.enums import FirstTurn
from app.models.schemas import RunConfig
from app.models.test_case import TestCase
from app.models.voice_simulation_job import VoiceSimulationJob
from fastapi import WebSocket
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from voice_runner.bot.dtmf_audio_emitter import PersonaFirstReplyDtmfProcessor
from voice_runner.persona import build_persona_system_prompt
from voice_runner.services import build_llm_service, build_stt_tts_services
from voice_runner.settings import WorkerSettings

logger = logging.getLogger(__name__)


async def run_pipecat_voice_call(
    *,
    websocket: WebSocket,
    stream_sid: str,
    call_sid: str,
    job: VoiceSimulationJob,
    test_case: TestCase,
    run_config: RunConfig,
    worker_settings: WorkerSettings,
) -> None:
    sid = connexity_settings.TWILIO_ACCOUNT_SID
    tok = connexity_settings.TWILIO_AUTH_TOKEN
    if not sid or not tok:
        msg = "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set"
        raise RuntimeError(msg)

    vad = SileroVADAnalyzer()

    serializer = TwilioFrameSerializer(
        stream_sid,
        call_sid=call_sid,
        account_sid=sid,
        auth_token=tok,
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

    persona_system_prompt = build_persona_system_prompt(test_case)
    stt, tts = build_stt_tts_services(
        job, run_config=run_config, shared_settings=worker_settings
    )
    llm = build_llm_service(
        run_config=run_config,
        test_case=test_case,
        persona_system_prompt=persona_system_prompt,
        worker_settings=worker_settings,
    )

    context_messages: list[dict[str, Any]] = [
        {"role": "system", "content": persona_system_prompt},
    ]
    llm_ctx = LLMContext(messages=context_messages)
    user_agg_params = LLMUserAggregatorParams(
        vad_analyzer=cast(VADAnalyzer, vad),
    )
    aggregation = LLMContextAggregatorPair(llm_ctx, user_params=user_agg_params)
    dtmf_gate = PersonaFirstReplyDtmfProcessor(
        dtmf_code=job.dtmf_code, sample_rate=8000
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            dtmf_gate,
            aggregation.user(),
            llm,
            tts,
            transport.output(),
            aggregation.assistant(),
        ],
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            allow_interruptions=True,
        ),
    )

    opener_task: dict[str, PipelineTask | None] = {"t": task}

    @transport.event_handler("on_client_connected")
    async def _on_connected(
        _transport: FastAPIWebsocketTransport, _ws: WebSocket
    ) -> None:
        pt = opener_task.get("t")
        if pt is None:
            return
        if test_case.first_turn != FirstTurn.USER:
            return
        text = (test_case.first_message or "").strip()
        if not text:
            return
        logger.info(
            "Queueing scripted user opener for job %s (first_turn=user)",
            job.id,
        )
        await pt.queue_frame(TTSSpeakFrame(text=text, append_to_context=True))

    runner = PipelineRunner(handle_sigint=False, handle_sigterm=False)

    logger.info(
        "Starting Pipecat pipeline job=%s stream_sid=%s call_sid=%s",
        job.id,
        stream_sid,
        call_sid,
    )

    await runner.run(task)
