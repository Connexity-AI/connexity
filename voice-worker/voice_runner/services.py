"""Map Connexity job + run config to Pipecat 1.2.1 STT/TTS/LLM services."""

from __future__ import annotations

from typing import Any, Protocol

from app.core.config import settings as connexity_settings
from app.models.enums import SimulatorMode
from app.models.schemas import RunConfig, UserSimulatorConfig
from app.models.voice_simulation_job import VoiceSimulationJob
from pipecat.services.anthropic.llm import AnthropicLLMService
from pipecat.services.cartesia.stt import CartesiaSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.services.stt_service import STTService
from pipecat.services.tts_service import TTSService
from pipecat.transcriptions.language import Language

from voice_runner.settings import WorkerSettings

PipelineLlm = AnthropicLLMService | GoogleLLMService | OpenAILLMService

STT_SAMPLE_RATE = 8000


class PersonaTestCaseLike(Protocol):
    persona_context: Any
    user_context: Any | None
    expected_outcomes: Any | None


class SimulatorRunLike(Protocol):
    user_simulator: UserSimulatorConfig | None


def _ensure_llm(sim: UserSimulatorConfig) -> None:
    if sim.mode != SimulatorMode.LLM:
        msg = "Voice worker currently supports llm simulator mode only (not scripted)."
        raise ValueError(msg)


def build_stt_tts_services(
    job: VoiceSimulationJob,
    *,
    run_config: RunConfig | None = None,
    shared_settings: WorkerSettings | None = None,
) -> tuple[STTService, TTSService]:
    """Construct STT/TTS Pipecat services from job wiring."""
    _ = run_config
    _ = shared_settings
    provider_stt = (job.stt_provider or "").lower().strip()
    provider_tts = (job.tts_provider or "").lower().strip()

    # STT providers are driven by persona audio input (no separate deepgram-vs-openai coupling).
    if provider_stt == "deepgram":
        k = connexity_settings.DEEPGRAM_API_KEY
        if not k:
            msg = "DEEPGRAM_API_KEY is required for deepgram STT"
            raise ValueError(msg)
        stt = DeepgramSTTService(
            api_key=k,
            sample_rate=STT_SAMPLE_RATE,
            encoding="linear16",
            channels=1,
            settings=DeepgramSTTService.Settings(
                model=job.stt_model,
                language=Language.EN,
                interim_results=True,
            ),
        )
    elif provider_stt == "openai":
        k = connexity_settings.OPENAI_API_KEY
        if not k:
            msg = "OPENAI_API_KEY is required for openai STT"
            raise ValueError(msg)
        stt = OpenAISTTService(
            api_key=k,
            sample_rate=STT_SAMPLE_RATE,
            settings=OpenAISTTService.Settings(
                model=job.stt_model, language=Language.EN
            ),
        )
    elif provider_stt == "cartesia":
        k = connexity_settings.CARTESIA_API_KEY
        if not k:
            msg = "CARTESIA_API_KEY is required for cartesia STT"
            raise ValueError(msg)
        stt = CartesiaSTTService(
            api_key=k,
            sample_rate=STT_SAMPLE_RATE,
            encoding="pcm_s16le",
            settings=CartesiaSTTService.Settings(
                model=job.stt_model,
                language=Language.EN.value,
            ),
        )
    else:
        msg = f"Unsupported voice STT provider: {job.stt_provider}"
        raise ValueError(msg)

    # TTS
    if provider_tts == "elevenlabs":
        k = connexity_settings.ELEVENLABS_API_KEY
        if not k:
            msg = "ELEVENLABS_API_KEY is required for elevenlabs TTS"
            raise ValueError(msg)
        tts = ElevenLabsTTSService(
            api_key=k,
            settings=ElevenLabsTTSService.Settings(
                model=job.tts_model,
                voice=job.tts_voice_id,
            ),
            sample_rate=STT_SAMPLE_RATE,
        )
    elif provider_tts == "cartesia":
        k = connexity_settings.CARTESIA_API_KEY
        if not k:
            msg = "CARTESIA_API_KEY is required for cartesia TTS"
            raise ValueError(msg)
        tts = CartesiaTTSService(
            api_key=k,
            sample_rate=STT_SAMPLE_RATE,
            encoding="pcm_s16le",
            settings=CartesiaTTSService.Settings(
                model=job.tts_model,
                voice=job.tts_voice_id,
            ),
        )
    elif provider_tts == "openai":
        k = connexity_settings.OPENAI_API_KEY
        if not k:
            msg = "OPENAI_API_KEY is required for openai TTS"
            raise ValueError(msg)
        tts = OpenAITTSService(
            api_key=k,
            settings=OpenAITTSService.Settings(
                model=job.tts_model,
                voice=job.tts_voice_id,
            ),
        )
    else:
        msg = f"Unsupported voice TTS provider: {job.tts_provider}"
        raise ValueError(msg)

    return stt, tts


def build_llm_service(
    *,
    run_config: SimulatorRunLike,
    test_case: PersonaTestCaseLike,
    persona_system_prompt: str,
    worker_settings: WorkerSettings,
) -> PipelineLlm:
    sim = run_config.user_simulator
    if sim is None:
        msg = "user_simulator is required on the run snapshot"
        raise ValueError(msg)
    _ensure_llm(sim)
    _ = test_case  # Prompt is assembled in `persona_system_prompt`; keep for API symmetry.

    model = sim.model or connexity_settings.LLM_DEFAULT_MODEL
    provider = (
        (sim.provider or connexity_settings.LLM_DEFAULT_PROVIDER or "openai")
        .lower()
        .strip()
    )
    temperature = sim.temperature if sim.temperature is not None else 0.7

    if provider == "openai":
        k = connexity_settings.OPENAI_API_KEY
        if not k:
            msg = "OPENAI_API_KEY is required for openai simulator provider"
            raise ValueError(msg)
        return OpenAILLMService(
            api_key=k,
            settings=OpenAILLMService.Settings(
                model=model,
                temperature=temperature,
                system_instruction=persona_system_prompt,
            ),
        )

    if provider == "anthropic":
        k = connexity_settings.ANTHROPIC_API_KEY
        if not k:
            msg = "ANTHROPIC_API_KEY is required for anthropic simulator provider"
            raise ValueError(msg)
        # Anthropic API temperature max is 1.0
        temp = min(float(temperature), 1.0)
        return AnthropicLLMService(
            api_key=k,
            settings=AnthropicLLMService.Settings(
                model=model,
                temperature=temp,
                system_instruction=persona_system_prompt,
            ),
        )

    if provider == "google":
        _ = worker_settings
        k = connexity_settings.google_llm_api_key()
        if not k:
            msg = "GOOGLE_GENAI_API_KEY or GOOGLE_API_KEY is required for google simulator provider"
            raise ValueError(msg)
        return GoogleLLMService(
            api_key=k,
            settings=GoogleLLMService.Settings(
                model=model,
                temperature=temperature,
                system_instruction=persona_system_prompt,
            ),
        )

    msg = f"Unsupported simulator LLM provider for voice worker: {provider}"
    raise ValueError(msg)


def smoke_imports() -> dict[str, Any]:
    """Lightweight import check for tests."""
    return {
        "deepgram": DeepgramSTTService,
        "openai_stt": OpenAISTTService,
        "cartesia_stt": CartesiaSTTService,
        "elevenlabs_tts": ElevenLabsTTSService,
        "cartesia_tts": CartesiaTTSService,
        "openai_tts": OpenAITTSService,
        "openai_llm": OpenAILLMService,
        "anthropic_llm": AnthropicLLMService,
        "google_llm": GoogleLLMService,
    }
