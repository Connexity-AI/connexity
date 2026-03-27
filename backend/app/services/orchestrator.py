"""Partial run orchestration: agent HTTP calls, message mapping, scenario loop."""

import asyncio
import logging
import statistics
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from app.models.agent_contract import (
    AgentRequest,
    AgentRequestMetadata,
    AgentResponse,
    ChatMessage,
)
from app.models.enums import ErrorCategory, SimulatorMode, TurnRole
from app.models.scenario import Scenario
from app.models.scenario_result import ScenarioResult
from app.models.schemas import (
    AggregateMetrics,
    ConversationTurn,
    JudgeVerdict,
    Persona,
    RunConfig,
    SimulatorConfig,
    ToolCall,
)
from app.services.judge import JudgeInput, evaluate_transcript
from app.services.llm import LLMMessage
from app.services.user_simulator import UserSimulator

logger = logging.getLogger(__name__)


class AgentCallError(Exception):
    """Agent endpoint request failed (network, timeout, or HTTP error)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def build_conversation_turn(
    *,
    index: int,
    role: TurnRole,
    content: str | None = None,
    latency_ms: int | None = None,
    tool_calls: list[ToolCall] | None = None,
    tool_call_id: str | None = None,
    token_count: int | None = None,
    timestamp: datetime | None = None,
) -> ConversationTurn:
    return ConversationTurn(
        index=index,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_call_id=tool_call_id,
        latency_ms=latency_ms,
        token_count=token_count,
        timestamp=timestamp or datetime.now(UTC),
    )


def transcript_to_agent_messages(
    transcript: list[ConversationTurn],
) -> list[ChatMessage]:
    """Map stored turns to the agent wire format (roles unchanged)."""
    return [
        ChatMessage(
            role=t.role,
            content=t.content,
            tool_calls=t.tool_calls,
            tool_call_id=t.tool_call_id,
            name=None,
        )
        for t in transcript
    ]


def transcript_to_simulator_messages(
    transcript: list[ConversationTurn],
) -> list[LLMMessage]:
    """User/assistant text turns only, roles flipped for the simulator LLM."""
    out: list[LLMMessage] = []
    for t in transcript:
        if t.role in (TurnRole.SYSTEM, TurnRole.TOOL):
            continue
        if t.role == TurnRole.USER:
            text = (t.content or "").strip()
            if text:
                out.append(LLMMessage(role="assistant", content=text))
            continue
        if t.role == TurnRole.ASSISTANT:
            text = (t.content or "").strip()
            if t.tool_calls and not text:
                text = "[Assistant requested tool calls]"
            if text:
                out.append(LLMMessage(role="user", content=text))
    return out


def _persona_from_scenario(scenario: Scenario) -> Persona:
    if scenario.persona:
        return Persona.model_validate(scenario.persona)
    return Persona(
        type="user",
        description="A user interacting with the assistant.",
        instructions="Respond naturally and stay in character.",
    )


def _append_agent_response(
    transcript: list[ConversationTurn],
    response: AgentResponse,
    round_latency_ms: int,
) -> None:
    msgs = response.messages
    if not msgs:
        return
    last_i = len(msgs) - 1
    total_tokens = response.usage.total_tokens if response.usage else None
    for i, m in enumerate(msgs):
        idx = len(transcript)
        lat = round_latency_ms if i == last_i else None
        tok = total_tokens if i == last_i else None
        transcript.append(
            build_conversation_turn(
                index=idx,
                role=m.role,
                content=m.content,
                latency_ms=lat,
                tool_calls=m.tool_calls,
                tool_call_id=m.tool_call_id,
                token_count=tok,
            )
        )


async def call_agent(
    endpoint_url: str,
    messages: list[ChatMessage],
    timeout_ms: int,
    *,
    metadata: AgentRequestMetadata | None = None,
    client: httpx.AsyncClient | None = None,
) -> tuple[AgentResponse, int]:
    """POST :class:`AgentRequest` JSON to the agent; return response and latency ms."""
    payload = AgentRequest(
        messages=messages,
        metadata=metadata,
    ).model_dump(mode="json")
    timeout = httpx.Timeout(timeout_ms / 1000.0)
    owns_client = client is None
    client = client or httpx.AsyncClient()
    started = time.perf_counter()
    try:
        try:
            resp = await client.post(endpoint_url, json=payload, timeout=timeout)
        except httpx.TimeoutException as e:
            msg = f"Agent request timed out after {timeout_ms}ms"
            raise AgentCallError(msg) from e
        except httpx.RequestError as e:
            msg = f"Agent request failed: {e}"
            raise AgentCallError(msg) from e
    finally:
        if owns_client:
            await client.aclose()
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if resp.is_error:
        msg = f"Agent HTTP {resp.status_code}: {resp.text[:500]}"
        raise AgentCallError(msg, status_code=resp.status_code)
    try:
        data = resp.json()
    except ValueError as e:
        msg = "Agent response is not valid JSON"
        raise AgentCallError(msg) from e
    try:
        parsed = AgentResponse.model_validate(data)
    except ValidationError as e:
        msg = f"Agent response JSON does not match contract: {e}"
        raise AgentCallError(msg) from e
    return parsed, elapsed_ms


async def run_scenario(
    scenario: Scenario,
    agent_endpoint_url: str,
    config: RunConfig,
    *,
    cancel_event: asyncio.Event | None = None,
) -> list[ConversationTurn]:
    """Execute one scenario: initial user message, then agent / simulator turns.

    If ``scenario.initial_message`` is empty, the opening user line is produced by
    calling the simulator (LLM mode: first completion; scripted mode: first
    scripted line).

    Stops when ``scenario.max_turns`` agent rounds are done, scripted lines are
    exhausted, timeout is hit, or the agent call fails.
    """
    sim_cfg = config.simulator or SimulatorConfig()
    persona = _persona_from_scenario(scenario)
    initial = scenario.initial_message or ""
    simulator = UserSimulator(
        persona=persona,
        initial_message=initial,
        user_context=scenario.user_context,
        expected_outcomes=scenario.expected_outcomes,
        config=sim_cfg,
    )

    transcript: list[ConversationTurn] = []
    initial_stripped = (scenario.initial_message or "").strip()
    if initial_stripped:
        transcript.append(
            build_conversation_turn(
                index=0,
                role=TurnRole.USER,
                content=simulator.get_initial_message(),
            )
        )
    else:
        try:
            opening = await simulator.generate_message([])
        except RuntimeError as e:
            logger.warning(
                "Could not produce opening user message for scenario %s: %s",
                scenario.id,
                e,
            )
            return transcript
        total_tok = opening.token_usage.get("total_tokens")
        transcript.append(
            build_conversation_turn(
                index=0,
                role=TurnRole.USER,
                content=opening.content,
                latency_ms=opening.latency_ms,
                token_count=total_tok,
            )
        )

    max_agent_rounds = scenario.max_turns
    agent_rounds = 0
    started = time.perf_counter()
    timeout_ms = config.timeout_per_scenario_ms

    async with httpx.AsyncClient() as client:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                logger.warning("Scenario %s stopped: run cancelled", scenario.id)
                transcript.append(
                    build_conversation_turn(
                        index=len(transcript),
                        role=TurnRole.ASSISTANT,
                        content="[platform: run cancelled]",
                        latency_ms=None,
                    )
                )
                break

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if elapsed_ms >= timeout_ms:
                logger.warning(
                    "Scenario %s stopped: timeout %sms elapsed",
                    scenario.id,
                    timeout_ms,
                )
                transcript.append(
                    build_conversation_turn(
                        index=len(transcript),
                        role=TurnRole.ASSISTANT,
                        content=f"[platform: scenario timeout after {timeout_ms}ms]",
                        latency_ms=None,
                    )
                )
                break

            if max_agent_rounds is not None and agent_rounds >= max_agent_rounds:
                break

            agent_messages = transcript_to_agent_messages(transcript)
            meta = AgentRequestMetadata(
                scenario_id=str(scenario.id),
                turn_index=len(transcript),
            )
            remaining_ms = max(1, timeout_ms - elapsed_ms)
            try:
                response, round_latency = await call_agent(
                    agent_endpoint_url,
                    agent_messages,
                    timeout_ms=remaining_ms,
                    metadata=meta,
                    client=client,
                )
            except AgentCallError as e:
                logger.warning("Agent call failed for scenario %s: %s", scenario.id, e)
                transcript.append(
                    build_conversation_turn(
                        index=len(transcript),
                        role=TurnRole.ASSISTANT,
                        content=f"[agent_error] {e!s}",
                        latency_ms=None,
                    )
                )
                break

            agent_rounds += 1
            _append_agent_response(transcript, response, round_latency)

            if sim_cfg.mode == SimulatorMode.SCRIPTED and simulator.is_exhausted:
                break

            try:
                sim_messages = transcript_to_simulator_messages(transcript)
                sim_result = await simulator.generate_message(sim_messages)
            except RuntimeError as e:
                logger.warning("Simulator exhausted or failed: %s", e)
                break

            transcript.append(
                build_conversation_turn(
                    index=len(transcript),
                    role=TurnRole.USER,
                    content=sim_result.content,
                    latency_ms=sim_result.latency_ms,
                    token_count=None,
                )
            )

            if sim_cfg.mode == SimulatorMode.SCRIPTED and simulator.is_exhausted:
                break

    return transcript


async def run_scenario_with_evaluation(
    scenario: Scenario,
    agent_endpoint_url: str,
    config: RunConfig,
    *,
    agent_system_prompt: str | None = None,
    agent_tools: list[dict[str, Any]] | None = None,
    cancel_event: asyncio.Event | None = None,
) -> tuple[list[ConversationTurn], JudgeVerdict | None]:
    """Run simulation then judge the transcript; returns ``(transcript, verdict)``.

    If the transcript is empty, ``verdict`` is ``None``.
    """
    transcript = await run_scenario(
        scenario,
        agent_endpoint_url,
        config,
        cancel_event=cancel_event,
    )
    if not transcript:
        return transcript, None

    verdict = await evaluate_transcript(
        JudgeInput(
            transcript=transcript,
            scenario=scenario,
            agent_system_prompt=agent_system_prompt,
            agent_tools=agent_tools,
            judge_config=config.judge,
        )
    )
    return transcript, verdict


def compute_aggregate_metrics(
    results: list[ScenarioResult],
) -> AggregateMetrics:
    from app.models.schemas import ErrorCategoryCount

    total = len(results)
    if total == 0:
        return AggregateMetrics(
            total_scenarios=0,
            passed_count=0,
            failed_count=0,
            error_count=0,
            pass_rate=0.0,
        )

    passed = sum(1 for r in results if r.passed is True)
    failed = sum(
        1
        for r in results
        if r.passed is False and r.error_category == ErrorCategory.NONE
    )
    errors = sum(1 for r in results if r.error_category != ErrorCategory.NONE)

    latencies = [
        r.agent_latency_p50_ms for r in results if r.agent_latency_p50_ms is not None
    ]

    cat_counts = {}
    for r in results:
        if r.error_category != ErrorCategory.NONE:
            cat_counts[r.error_category] = cat_counts.get(r.error_category, 0) + 1

    dist = [ErrorCategoryCount(category=k, count=v) for k, v in cat_counts.items()]

    scores = [
        r.verdict.get("overall_score")
        for r in results
        if r.verdict and r.verdict.get("overall_score") is not None
    ]

    return AggregateMetrics(
        total_scenarios=total,
        passed_count=passed,
        failed_count=failed,
        error_count=errors,
        pass_rate=passed / total if total > 0 else 0.0,
        latency_p50_ms=statistics.median(latencies) if latencies else None,
        latency_p95_ms=statistics.quantiles(latencies, n=20)[18]
        if len(latencies) >= 20
        else None,
        latency_max_ms=max(latencies) if latencies else None,
        latency_avg_ms=statistics.mean(latencies) if latencies else None,
        error_category_distribution=dist,
        avg_overall_score=statistics.mean(scores) if scores else None,
    )


async def _execute_single_scenario(
    run_id: uuid.UUID,
    scenario: Scenario,
    agent_endpoint_url: str,
    config: RunConfig,
    agent_system_prompt: str | None,
    agent_tools: list[dict[str, Any]] | None,
    semaphore: asyncio.Semaphore,
    cancel_event: asyncio.Event,
) -> ScenarioResult:
    from sqlmodel import Session

    from app import crud
    from app.core.db import engine
    from app.models import ScenarioResultCreate, ScenarioResultUpdate
    from app.models.schemas import ScenarioProgressData
    from app.services.run_manager import run_manager

    with Session(engine) as session:
        result = crud.create_scenario_result(
            session=session,
            result_in=ScenarioResultCreate(
                run_id=run_id,
                scenario_id=scenario.id,
            ),
        )
        result_id = result.id

    async with semaphore:
        if cancel_event.is_set():
            return result

        run_manager.emit(
            run_id,
            "scenario_started",
            {"scenario_id": str(scenario.id), "scenario_name": scenario.name},
        )

        started_at = datetime.now(UTC)
        try:
            transcript, verdict = await run_scenario_with_evaluation(
                scenario=scenario,
                agent_endpoint_url=agent_endpoint_url,
                config=config,
                agent_system_prompt=agent_system_prompt,
                agent_tools=agent_tools,
                cancel_event=cancel_event,
            )
            completed_at = datetime.now(UTC)

            # Calculate metrics
            turn_count = len(transcript)
            total_latency_ms = int((completed_at - started_at).total_seconds() * 1000)

            agent_latencies = [
                t.latency_ms
                for t in transcript
                if t.role == TurnRole.ASSISTANT and t.latency_ms is not None
            ]
            p50 = int(statistics.median(agent_latencies)) if agent_latencies else None
            p95 = (
                int(statistics.quantiles(agent_latencies, n=20)[18])
                if len(agent_latencies) >= 20
                else (max(agent_latencies) if agent_latencies else None)
            )
            max_lat = max(agent_latencies) if agent_latencies else None

            update_data = ScenarioResultUpdate(
                transcript=transcript,
                turn_count=turn_count,
                verdict=verdict,
                total_latency_ms=total_latency_ms,
                agent_latency_p50_ms=p50,
                agent_latency_p95_ms=p95,
                agent_latency_max_ms=max_lat,
                passed=verdict.passed if verdict else False,
                error_category=verdict.error_category
                if verdict
                else ErrorCategory.NONE,
                started_at=started_at,
                completed_at=completed_at,
            )

        except Exception as e:
            logger.exception("Scenario %s failed unexpectedly", scenario.id)
            completed_at = datetime.now(UTC)
            update_data = ScenarioResultUpdate(
                passed=False,
                error_category=ErrorCategory.OTHER,
                error_message=str(e),
                started_at=started_at,
                completed_at=completed_at,
            )

        # Persist
        try:
            def _update_db():
                with Session(engine) as session:
                    db_result = crud.get_scenario_result(
                        session=session, result_id=result_id
                    )
                    if db_result:
                        return crud.update_scenario_result(
                            session=session,
                            db_result=db_result,
                            result_in=update_data,
                        )
                    return None

            updated_result = await asyncio.to_thread(_update_db)
        except Exception:
            logger.exception(
                "Failed to persist result for scenario %s in run %s",
                scenario.id,
                run_id,
            )
            updated_result = None

        # Update progress
        try:
            progress = run_manager.get_progress(run_id)
            if progress and updated_result:
                progress.completed_count += 1
                if updated_result.passed:
                    progress.passed_count += 1
                elif updated_result.error_category != ErrorCategory.NONE:
                    progress.error_count += 1
                else:
                    progress.failed_count += 1

                run_manager.emit(
                    run_id,
                    "scenario_completed",
                    ScenarioProgressData(
                        run_id=run_id,
                        scenario_id=scenario.id,
                        scenario_name=scenario.name,
                        completed_count=progress.completed_count,
                        total_count=progress.total_scenarios,
                        passed=updated_result.passed,
                        overall_score=updated_result.verdict.get("overall_score")
                        if updated_result.verdict
                        else None,
                        error_message=updated_result.error_message,
                    ).model_dump(mode="json"),
                )
        except Exception:
            logger.exception(
                "Failed to emit progress for scenario %s in run %s",
                scenario.id,
                run_id,
            )

        return updated_result or result


async def execute_run(run_id: uuid.UUID) -> None:
    """Top-level orchestration: load run + scenarios, execute concurrently, persist results."""
    from sqlmodel import Session

    from app import crud
    from app.core.db import engine
    from app.models import RunUpdate
    from app.models.enums import RunStatus
    from app.services.run_manager import run_manager

    state = run_manager.register(run_id)

    try:
        with Session(engine) as session:
            run = crud.get_run(session=session, run_id=run_id)
            if not run or run.status not in (
                RunStatus.PENDING,
                RunStatus.FAILED,
                RunStatus.CANCELLED,
            ):
                logger.error("Run %s not found or not in executable state", run_id)
                return

            crud.update_run(
                session=session,
                db_run=run,
                run_in=RunUpdate(
                    status=RunStatus.RUNNING, started_at=datetime.now(UTC)
                ),
            )

            scenarios = crud.get_scenarios_for_set(
                session=session, scenario_set_id=run.scenario_set_id
            )

            config = RunConfig.model_validate(run.config) if run.config else RunConfig()
            agent_endpoint_url = run.agent_endpoint_url
            agent_system_prompt = run.agent_system_prompt
            agent_tools = run.agent_tools

        state.progress.total_scenarios = len(scenarios)
        run_manager.emit(
            run_id,
            "run_started",
            {"run_id": str(run_id), "total_scenarios": len(scenarios)},
        )

        semaphore = asyncio.Semaphore(config.concurrency)
        tasks = [
            _execute_single_scenario(
                run_id=run_id,
                scenario=scenario,
                agent_endpoint_url=agent_endpoint_url,
                config=config,
                agent_system_prompt=agent_system_prompt,
                agent_tools=agent_tools,
                semaphore=semaphore,
                cancel_event=state.cancel_event,
            )
            for scenario in scenarios
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results: list[ScenarioResult] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.exception(
                    "Scenario task %d failed for run %s: %s",
                    i,
                    run_id,
                    r,
                    exc_info=r,
                )
            else:
                valid_results.append(r)

        aggregate_metrics = compute_aggregate_metrics(valid_results)

        with Session(engine) as session:
            db_run = crud.get_run(session=session, run_id=run_id)
            if db_run:
                final_status = (
                    RunStatus.CANCELLED
                    if state.cancel_event.is_set()
                    else RunStatus.COMPLETED
                )
                crud.update_run(
                    session=session,
                    db_run=db_run,
                    run_in=RunUpdate(
                        status=final_status,
                        completed_at=datetime.now(UTC),
                        aggregate_metrics=aggregate_metrics,
                    ),
                )

        event_name = "run_cancelled" if state.cancel_event.is_set() else "run_completed"
        run_manager.emit(run_id, event_name, {"run_id": str(run_id)})

    except Exception as e:
        logger.exception("Run %s failed unexpectedly", run_id)
        with Session(engine) as session:
            db_run = crud.get_run(session=session, run_id=run_id)
            if db_run:
                crud.update_run(
                    session=session,
                    db_run=db_run,
                    run_in=RunUpdate(
                        status=RunStatus.FAILED, completed_at=datetime.now(UTC)
                    ),
                )
        run_manager.emit(run_id, "run_failed", {"run_id": str(run_id), "error": str(e)})
    finally:
        run_manager.unregister(run_id)
