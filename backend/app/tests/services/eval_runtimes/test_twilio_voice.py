"""Twilio voice runtime tests."""

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from sqlmodel import Session

from app import crud
from app.models import VoiceSimulationJobUpdate, VoiceSimulationResultSubmit
from app.models.agent import Agent
from app.models.agent_contract import ChatMessage
from app.models.enums import (
    AgentMode,
    RunMode,
    TurnRole,
    VoiceRuntimeKind,
    VoiceSimulationJobStatus,
)
from app.models.schemas import (
    RunConfig,
    SttConfig,
    TtsConfig,
    TwilioVoiceRuntimeConfig,
    UserSimulatorConfig,
)
from app.services.eval_runtimes import (
    AgentSnapshot,
    RunSnapshot,
    RuntimeRunArgs,
    get_runtime,
)
from app.services.eval_runtimes.voice.twilio import TwilioVoiceRuntime
from app.services.orchestrator import _execute_single_test_case
from app.services.run_manager import RunManager
from app.services.voice_simulation_results import submit_voice_simulation_result
from app.tests.utils.eval import (
    create_test_case_fixture,
    create_test_case_result_fixture,
    create_test_eval_config,
    create_test_run,
    eval_config_members,
)


def _voice_run_config(
    *,
    timeout_ms: int | None = None,
    max_call_duration_seconds: int | None = None,
) -> RunConfig:
    config_kwargs: dict[str, object] = {
        "mode": RunMode.VOICE,
        "agent_phone_number": "+15551234567",
        "runtime": TwilioVoiceRuntimeConfig(),
        "user_simulator": UserSimulatorConfig(
            stt=SttConfig(provider="deepgram", model="nova-3"),
            tts=TtsConfig(
                provider="elevenlabs",
                model="eleven_flash_v2_5",
                voice_id="test-voice",
            ),
        ),
    }
    if timeout_ms is not None:
        config_kwargs["timeout_per_test_case_ms"] = timeout_ms
    if max_call_duration_seconds is not None:
        config_kwargs["max_call_duration_seconds"] = max_call_duration_seconds
    elif timeout_ms is not None:
        timeout_seconds = timeout_ms // 1000
        config_kwargs["max_call_duration_seconds"] = max(1, timeout_seconds - 1)
    return RunConfig(**config_kwargs)


def _setup_voice_context(db: Session):
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(test_case.id))
    run = create_test_run(
        db, agent_id=eval_config.agent_id, eval_config_id=eval_config.id
    )
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    return run, test_case, result


def _make_agent_snapshot(agent: Agent) -> AgentSnapshot:
    return AgentSnapshot(
        agent=agent,
        agent_id=agent.id,
        platform=agent.platform,
        integration_id=agent.integration_id,
        platform_agent_id=agent.platform_agent_id,
        endpoint_url=agent.endpoint_url,
        system_prompt=agent.system_prompt,
        tools=agent.tools,
        mode=AgentMode.ENDPOINT,
        model=None,
        provider=None,
    )


async def _submit_result_when_job_created(
    db: Session,
    *,
    run_id: uuid.UUID,
) -> None:
    for _ in range(100):
        jobs, _count = crud.list_voice_simulation_jobs(session=db, run_id=run_id)
        if jobs:
            job = jobs[0]
            crud.update_voice_simulation_job(
                session=db,
                db_job=job,
                job_in=VoiceSimulationJobUpdate(
                    status=VoiceSimulationJobStatus.WAITING_FOR_RESULT,
                    call_ended_at=datetime.now(UTC),
                ),
            )
            submit_voice_simulation_result(
                session=db,
                payload=VoiceSimulationResultSubmit(
                    audio_url=f"mock-dtmf://{job.dtmf_code}",
                    messages=[
                        ChatMessage(
                            role=TurnRole.USER,
                            content="I need help with my order.",
                        ),
                        ChatMessage(
                            role=TurnRole.ASSISTANT,
                            content="Sure, I can help with that.",
                        ),
                    ],
                ),
            )
            return
        await asyncio.sleep(0.05)
    msg = "Voice job was not created in time"
    raise AssertionError(msg)


def test_get_runtime_returns_twilio_voice_runtime() -> None:
    runtime = get_runtime(RunMode.VOICE, VoiceRuntimeKind.TWILIO)
    assert isinstance(runtime, TwilioVoiceRuntime)


async def test_twilio_voice_runtime_end_to_end(db: Session) -> None:
    run, test_case, result = _setup_voice_context(db)
    agent = crud.get_agent(session=db, agent_id=run.agent_id)
    assert agent is not None

    runtime = TwilioVoiceRuntime()
    args = RuntimeRunArgs(
        test_case=test_case,
        agent_snapshot=_make_agent_snapshot(agent),
        run_snapshot=RunSnapshot(
            run_id=run.id,
            run_config=_voice_run_config(),
            cancel_event=asyncio.Event(),
        ),
        test_case_result_id=result.id,
    )

    submit_task = asyncio.create_task(
        _submit_result_when_job_created(db, run_id=run.id)
    )
    try:
        run_out = await runtime.run_test_case(
            TwilioVoiceRuntimeConfig(),
            args,
            db,
        )
    finally:
        await submit_task

    assert len(run_out.transcript) == 2
    assert run_out.transcript[0].role == TurnRole.USER
    assert run_out.transcript[1].role == TurnRole.ASSISTANT
    assert run_out.runtime_metadata is not None
    assert "voice_simulation_job_id" in run_out.runtime_metadata

    jobs, count = crud.list_voice_simulation_jobs(session=db, run_id=run.id)
    assert count == 1
    assert jobs[0].status == VoiceSimulationJobStatus.COMPLETED
    assert jobs[0].test_case_result_id == result.id
    assert jobs[0].max_call_duration_seconds == 300


async def test_orchestrator_executes_twilio_voice_runtime(db: Session) -> None:
    run, test_case, _result = _setup_voice_context(db)
    agent = crud.get_agent(session=db, agent_id=run.agent_id)
    assert agent is not None

    voice_config = _voice_run_config(timeout_ms=10_000)
    run_id = run.id
    manager = RunManager()
    state = manager.register(run_id)

    submit_task = asyncio.create_task(
        _submit_result_when_job_created(db, run_id=run_id)
    )
    try:
        with (
            patch("app.services.run_manager.run_manager", manager),
            patch(
                "app.services.orchestrator.evaluate_transcript",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            updated = await _execute_single_test_case(
                run_id=run_id,
                test_case=test_case,
                agent_snapshot=_make_agent_snapshot(agent),
                run_snapshot=RunSnapshot(
                    run_id=run_id,
                    run_config=voice_config,
                    cancel_event=state.cancel_event,
                ),
                semaphore=asyncio.Semaphore(1),
            )
    finally:
        await submit_task

    assert updated is not None
    assert updated.transcript is not None
    assert len(updated.transcript) == 2

    jobs, count = crud.list_voice_simulation_jobs(session=db, run_id=run_id)
    assert count == 1
    assert jobs[0].status == VoiceSimulationJobStatus.COMPLETED
