"""Partial run orchestration: agent HTTP calls, message mapping, test_case loop."""

import asyncio
import logging
import statistics
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.models.agent_contract import (
    AgentRequest,
    AgentRequestMetadata,
    AgentResponse,
    ChatMessage,
    TokenUsage,
)
from app.models.enums import AgentMode, FirstTurn, SimulatorMode, TurnRole
from app.models.schemas import (
    AggregateMetrics,
    ConversationTurn,
    JudgeVerdict,
    RunConfig,
    ToolCall,
    UserSimulatorConfig,
)
from app.models.test_case import TestCase
from app.models.test_case_result import TestCaseResult
from app.services.agent_simulator import AgentSimulator
from app.services.agent_tool_definitions import snapshot_marks_tool_terminating
from app.services.cost_tracker import (
    TestCaseTokenAccumulator,
    estimate_agent_cost,
    estimate_agent_tokens,
    sum_platform_usage_dicts,
    sum_usage_dicts,
)
from app.services.judge import JudgeInput, evaluate_transcript
from app.services.llm import LLMMessage
from app.services.tool_dispatch import build_tool_executor
from app.services.user_simulator import UserSimulator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _agent_http_client(agent_mode: AgentMode):
    """HTTP client only for endpoint-mode agents."""
    if agent_mode == AgentMode.ENDPOINT:
        async with httpx.AsyncClient() as client:
            yield client
    else:
        yield None


@dataclass(frozen=True)
class TestCaseRunResult:
    """Outcome of :func:`run_test_case` including token/cost aggregates (simulator only)."""

    transcript: list[ConversationTurn]
    agent_token_usage: dict[str, int | bool]
    platform_token_usage: dict[str, int]
    agent_cost_usd: float = 0.0
    platform_cost_usd: float = 0.0


def _reported_agent_usage(usage: TokenUsage | None) -> dict[str, int] | None:
    """Non-empty usage dict from agent-reported :class:`TokenUsage`, or ``None``."""
    if usage is None:
        return None
    out: dict[str, int] = {}
    if usage.prompt_tokens is not None:
        out["prompt_tokens"] = usage.prompt_tokens
    if usage.completion_tokens is not None:
        out["completion_tokens"] = usage.completion_tokens
    if usage.total_tokens is not None:
        out["total_tokens"] = usage.total_tokens
    return out if out else None


class AgentCallError(Exception):
    """Agent endpoint request failed (network, timeout, or HTTP error)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _turns_have_terminating_assistant_tool_call(
    turns: list[ConversationTurn],
    agent_tools: list[dict[str, Any]] | None,
) -> bool:
    """True if any assistant turn requests a tool marked terminating on the snapshot."""
    if not agent_tools:
        return False
    for t in turns:
        if t.role != TurnRole.ASSISTANT or not t.tool_calls:
            continue
        for tc in t.tool_calls:
            if snapshot_marks_tool_terminating(tc.function.name, agent_tools):
                return True
    return False


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


# ── Turn-step helpers ─────────────────────────────────────────────────


async def _do_agent_turn(
    transcript: list[ConversationTurn],
    test_case: TestCase,
    agent_endpoint_url: str | None,
    agent_mode: AgentMode,
    agent_system_prompt: str | None,
    agent_tools: list[dict[str, Any]] | None,
    agent_simulator: AgentSimulator | None,
    acc: TestCaseTokenAccumulator,
    timeout_ms: int,
    started: float,
    client: httpx.AsyncClient | None,
) -> bool:
    """Execute one agent turn. Returns False if the loop should break."""
    agent_messages = transcript_to_agent_messages(transcript)
    meta = AgentRequestMetadata(
        test_case_id=str(test_case.id),
        turn_index=len(transcript),
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    remaining_ms = max(1, timeout_ms - elapsed_ms)

    if agent_mode == AgentMode.PLATFORM:
        assert agent_simulator is not None
        try:
            plat = await agent_simulator.generate_response(agent_messages)
        except Exception as e:
            logger.warning(
                "Platform agent simulator failed for test_case %s: %s",
                test_case.id,
                e,
            )
            transcript.append(
                build_conversation_turn(
                    index=len(transcript),
                    role=TurnRole.ASSISTANT,
                    content=f"[agent_error] {e!s}",
                    latency_ms=None,
                )
            )
            return False

        usage_map = plat.token_usage
        if usage_map:
            acc.add_agent_usage(usage_map)
        if plat.cost_usd is not None:
            acc.add_agent_cost(plat.cost_usd)
        response = AgentResponse(
            messages=plat.messages,
            model=plat.model,
            provider=plat.provider,
            usage=TokenUsage(
                prompt_tokens=usage_map.get("prompt_tokens"),
                completion_tokens=usage_map.get("completion_tokens"),
                total_tokens=usage_map.get("total_tokens"),
            ),
        )
        _append_agent_response(transcript, response, plat.latency_ms)
    else:
        if not agent_endpoint_url:
            logger.error("Endpoint mode missing agent_endpoint_url")
            transcript.append(
                build_conversation_turn(
                    index=len(transcript),
                    role=TurnRole.ASSISTANT,
                    content="[agent_error] missing agent endpoint URL",
                    latency_ms=None,
                )
            )
            return False
        assert client is not None
        try:
            response, round_latency = await call_agent(
                agent_endpoint_url,
                agent_messages,
                timeout_ms=remaining_ms,
                metadata=meta,
                client=client,
            )
        except AgentCallError as e:
            logger.warning("Agent call failed for test_case %s: %s", test_case.id, e)
            transcript.append(
                build_conversation_turn(
                    index=len(transcript),
                    role=TurnRole.ASSISTANT,
                    content=f"[agent_error] {e!s}",
                    latency_ms=None,
                )
            )
            return False

        reported = _reported_agent_usage(response.usage)
        if reported is not None:
            acc.add_agent_usage(reported)
        else:
            estimated = estimate_agent_tokens(
                prompt_messages=agent_messages,
                response_messages=response.messages,
                agent_system_prompt=agent_system_prompt,
                agent_tools=agent_tools,
                model=response.model,
                fallback_model=settings.default_llm_id,
            )
            acc.add_agent_usage(estimated)
            reported = estimated

        if reported.get("prompt_tokens") or reported.get("completion_tokens"):
            acc.add_agent_cost(
                estimate_agent_cost(
                    model=response.model,
                    provider=response.provider,
                    usage=reported,
                )
            )

        _append_agent_response(transcript, response, round_latency)

    return True


async def _do_user_turn(
    transcript: list[ConversationTurn],
    simulator: UserSimulator,
    sim_cfg: UserSimulatorConfig,
    acc: TestCaseTokenAccumulator,
) -> bool:
    """Execute one user simulator turn. Returns False if the loop should break."""
    if sim_cfg.mode == SimulatorMode.SCRIPTED and simulator.is_exhausted:
        return False

    try:
        sim_messages = transcript_to_simulator_messages(transcript)
        sim_result = await simulator.generate_message(sim_messages)
    except RuntimeError as e:
        logger.warning("Simulator exhausted or failed: %s", e)
        return False

    if sim_result.token_usage:
        acc.add_platform_usage(dict(sim_result.token_usage))
    acc.add_platform_cost(sim_result.cost_usd)
    sim_total = sim_result.token_usage.get("total_tokens")
    transcript.append(
        build_conversation_turn(
            index=len(transcript),
            role=TurnRole.USER,
            content=sim_result.content,
            latency_ms=sim_result.latency_ms,
            token_count=sim_total,
        )
    )

    if sim_cfg.mode == SimulatorMode.SCRIPTED and simulator.is_exhausted:
        return False

    return True


# ── Main test case runner ─────────────────────────────────────────────


async def run_test_case(
    test_case: TestCase,
    agent_endpoint_url: str | None,
    config: RunConfig,
    *,
    agent_mode: AgentMode = AgentMode.ENDPOINT,
    agent_model: str | None = None,
    agent_provider: str | None = None,
    agent_system_prompt: str | None = None,
    agent_tools: list[dict[str, Any]] | None = None,
    cancel_event: asyncio.Event | None = None,
    platform_tool_executor_mode: Literal["mock", "live", "synthetic"] | None = None,
) -> TestCaseRunResult:
    """Execute one test_case conversation.

    Respects ``test_case.first_turn`` to decide who speaks first (agent or
    persona).  ``test_case.first_message`` provides the opening line for
    whoever goes first; when absent, the opener is LLM-generated.

    Stops when ``config.max_turns`` agent rounds are done, scripted lines are
    exhausted, timeout is hit, a terminating tool call is invoked, or the agent call fails.
    """
    sim_cfg = config.user_simulator or UserSimulatorConfig()
    first_message_text = (test_case.first_message or "").strip()
    first_turn = test_case.first_turn or FirstTurn.USER

    simulator = UserSimulator(
        persona_context=test_case.persona_context,
        initial_message=first_message_text if first_turn == FirstTurn.USER else "",
        user_context=test_case.user_context,
        expected_outcomes=test_case.expected_outcomes,
        config=sim_cfg,
    )

    agent_simulator: AgentSimulator | None = None
    if agent_mode == AgentMode.PLATFORM:
        model_id = (agent_model or "").strip()
        if not model_id:
            logger.error(
                "Platform agent mode requires agent_model on the run snapshot; test_case %s",
                test_case.id,
            )
        effective_tool_mode: Literal["mock", "live", "synthetic"] = (
            platform_tool_executor_mode
            if platform_tool_executor_mode is not None
            else config.tool_mode
        )
        tool_executor = build_tool_executor(
            tools=agent_tools,
            expected_tool_calls=test_case.expected_tool_calls,
            test_case_context=test_case.user_context or {},
            tool_mode=effective_tool_mode,
        )
        agent_simulator = AgentSimulator(
            system_prompt=agent_system_prompt or "",
            tools=agent_tools,
            agent_model=model_id or settings.default_llm_id,
            agent_provider=agent_provider,
            config=config.agent_simulator,
            tool_executor=tool_executor,
        )

    acc = TestCaseTokenAccumulator()
    transcript: list[ConversationTurn] = []

    # ── Initial message ──────────────────────────────────────────────
    if first_turn == FirstTurn.USER:
        # Persona speaks first
        if first_message_text:
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
                    "Could not produce opening user message for test_case %s: %s",
                    test_case.id,
                    e,
                )
                return TestCaseRunResult(
                    transcript=transcript,
                    agent_token_usage=acc.agent_token_usage,
                    platform_token_usage=acc.platform_token_usage,
                    agent_cost_usd=acc.agent_cost_usd,
                    platform_cost_usd=acc.platform_cost_usd,
                )
            if opening.token_usage:
                acc.add_platform_usage(dict(opening.token_usage))
            acc.add_platform_cost(opening.cost_usd)
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
    else:
        # Agent speaks first
        if first_message_text:
            transcript.append(
                build_conversation_turn(
                    index=0,
                    role=TurnRole.ASSISTANT,
                    content=first_message_text,
                )
            )
        else:
            # Generate agent's opening by calling the agent with no prior messages
            # (handled by _do_agent_turn with an empty transcript)
            pass

    max_agent_rounds = config.max_turns
    agent_rounds = 0
    started = time.perf_counter()
    timeout_ms = config.timeout_per_test_case_ms

    # If agent spoke first via first_message, count it as a round
    if first_turn == FirstTurn.AGENT and first_message_text:
        agent_rounds += 1

    async with _agent_http_client(agent_mode) as client:
        # For agent-first without first_message, generate the opening
        if first_turn == FirstTurn.AGENT and not first_message_text:
            turn_before = len(transcript)
            ok = await _do_agent_turn(
                transcript,
                test_case,
                agent_endpoint_url,
                agent_mode,
                agent_system_prompt,
                agent_tools,
                agent_simulator,
                acc,
                timeout_ms,
                started,
                client,
            )
            if not ok:
                return TestCaseRunResult(
                    transcript=transcript,
                    agent_token_usage=acc.agent_token_usage,
                    platform_token_usage=acc.platform_token_usage,
                    agent_cost_usd=acc.agent_cost_usd,
                    platform_cost_usd=acc.platform_cost_usd,
                )
            if _turns_have_terminating_assistant_tool_call(
                transcript[turn_before:], agent_tools
            ):
                return TestCaseRunResult(
                    transcript=transcript,
                    agent_token_usage=acc.agent_token_usage,
                    platform_token_usage=acc.platform_token_usage,
                    agent_cost_usd=acc.agent_cost_usd,
                    platform_cost_usd=acc.platform_cost_usd,
                )
            agent_rounds += 1

        while True:
            if cancel_event is not None and cancel_event.is_set():
                logger.warning("TestCase %s stopped: run cancelled", test_case.id)
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
                    "TestCase %s stopped: timeout %sms elapsed",
                    test_case.id,
                    timeout_ms,
                )
                transcript.append(
                    build_conversation_turn(
                        index=len(transcript),
                        role=TurnRole.ASSISTANT,
                        content=f"[platform: test_case timeout after {timeout_ms}ms]",
                        latency_ms=None,
                    )
                )
                break

            if max_agent_rounds is not None and agent_rounds >= max_agent_rounds:
                break

            if first_turn == FirstTurn.USER:
                # Persona-first: agent responds → user responds
                turn_before = len(transcript)
                ok = await _do_agent_turn(
                    transcript,
                    test_case,
                    agent_endpoint_url,
                    agent_mode,
                    agent_system_prompt,
                    agent_tools,
                    agent_simulator,
                    acc,
                    timeout_ms,
                    started,
                    client,
                )
                if not ok:
                    break
                if _turns_have_terminating_assistant_tool_call(
                    transcript[turn_before:], agent_tools
                ):
                    break
                agent_rounds += 1

                # End on the agent's last reply: skip the trailing user turn
                # that nothing would read.
                if max_agent_rounds is not None and agent_rounds >= max_agent_rounds:
                    break

                ok = await _do_user_turn(transcript, simulator, sim_cfg, acc)
                if not ok:
                    break
            else:
                # Agent-first: user responds → agent responds
                ok = await _do_user_turn(transcript, simulator, sim_cfg, acc)
                if not ok:
                    break

                # Re-check max_turns before agent turn
                if max_agent_rounds is not None and agent_rounds >= max_agent_rounds:
                    break

                turn_before = len(transcript)
                ok = await _do_agent_turn(
                    transcript,
                    test_case,
                    agent_endpoint_url,
                    agent_mode,
                    agent_system_prompt,
                    agent_tools,
                    agent_simulator,
                    acc,
                    timeout_ms,
                    started,
                    client,
                )
                if not ok:
                    break
                if _turns_have_terminating_assistant_tool_call(
                    transcript[turn_before:], agent_tools
                ):
                    break
                agent_rounds += 1

    return TestCaseRunResult(
        transcript=transcript,
        agent_token_usage=acc.agent_token_usage,
        platform_token_usage=acc.platform_token_usage,
        agent_cost_usd=acc.agent_cost_usd,
        platform_cost_usd=acc.platform_cost_usd,
    )


async def run_test_case_with_evaluation(
    test_case: TestCase,
    agent_endpoint_url: str | None,
    config: RunConfig,
    *,
    agent_mode: AgentMode = AgentMode.ENDPOINT,
    agent_model: str | None = None,
    agent_provider: str | None = None,
    agent_system_prompt: str | None = None,
    agent_tools: list[dict[str, Any]] | None = None,
    cancel_event: asyncio.Event | None = None,
    platform_tool_executor_mode: Literal["mock", "live", "synthetic"] | None = None,
) -> tuple[TestCaseRunResult, JudgeVerdict | None]:
    """Run simulation then judge the transcript.

    Returns ``(run_result, verdict)``. If the transcript is empty, ``verdict`` is
    ``None``.
    """
    run_out = await run_test_case(
        test_case,
        agent_endpoint_url,
        config,
        agent_mode=agent_mode,
        agent_model=agent_model,
        agent_provider=agent_provider,
        agent_system_prompt=agent_system_prompt,
        agent_tools=agent_tools,
        cancel_event=cancel_event,
        platform_tool_executor_mode=platform_tool_executor_mode,
    )
    if not run_out.transcript:
        return run_out, None

    verdict = await evaluate_transcript(
        JudgeInput(
            transcript=run_out.transcript,
            test_case=test_case,
            agent_system_prompt=agent_system_prompt,
            agent_tools=agent_tools,
            judge_config=config.judge,
        )
    )
    return run_out, verdict


def _derive_test_case_passed(verdict: JudgeVerdict | None) -> bool:
    """Compute whether a single test case execution passed.

    Per CS-127: a test case passes when *all* of its expected_outcomes pass.
    For legacy test cases without expected_outcomes (or when the judge could
    not produce them), fall back to the judge's overall_score-based verdict.
    """
    if verdict is None:
        return False
    if verdict.expected_outcome_results:
        return all(o.passed for o in verdict.expected_outcome_results)
    return verdict.passed


def compute_aggregate_metrics(
    results: list[TestCaseResult],
    *,
    metrics_pass_threshold: float | None = None,
    cases_pass_threshold: float | None = None,
) -> AggregateMetrics:
    total_executions = len(results)
    if total_executions == 0:
        return AggregateMetrics(
            unique_test_case_count=0,
            total_executions=0,
            passed_count=0,
            failed_count=0,
            error_count=0,
            pass_rate=0.0,
            metrics_pass_threshold=metrics_pass_threshold,
            cases_pass_threshold=cases_pass_threshold,
        )

    unique_test_case_count = len({r.test_case_id for r in results})
    passed = sum(1 for r in results if r.passed is True)
    errored = sum(1 for r in results if r.error_message is not None)
    failed = sum(1 for r in results if r.passed is False and r.error_message is None)

    latencies = [
        r.agent_latency_p50_ms for r in results if r.agent_latency_p50_ms is not None
    ]

    scores = [
        r.verdict.get("overall_score")
        for r in results
        if r.verdict and r.verdict.get("overall_score") is not None
    ]

    agent_parts = [r.agent_token_usage for r in results if r.agent_token_usage]
    total_agent = sum_usage_dicts(*agent_parts) if agent_parts else None
    if not total_agent:
        total_agent = None

    platform_parts = [r.platform_token_usage for r in results if r.platform_token_usage]
    total_platform = (
        sum_platform_usage_dicts(*platform_parts) if platform_parts else None
    )
    if not total_platform:
        total_platform = None

    agent_costs = [r.agent_cost_usd for r in results if r.agent_cost_usd is not None]
    platform_costs = [
        r.platform_cost_usd for r in results if r.platform_cost_usd is not None
    ]
    cost_values = [
        r.estimated_cost_usd for r in results if r.estimated_cost_usd is not None
    ]
    total_cost_usd = sum(cost_values) if cost_values else None

    pass_rate = passed / total_executions if total_executions > 0 else 0.0
    weighted_metrics_score_pct = statistics.mean(scores) if scores else None
    cases_pass_rate_pct = pass_rate * 100.0

    metrics_passed: bool | None
    if metrics_pass_threshold is not None and weighted_metrics_score_pct is not None:
        metrics_passed = weighted_metrics_score_pct >= metrics_pass_threshold
    else:
        metrics_passed = None

    cases_passed: bool | None
    if cases_pass_threshold is not None:
        cases_passed = cases_pass_rate_pct >= cases_pass_threshold
    else:
        cases_passed = None

    return AggregateMetrics(
        unique_test_case_count=unique_test_case_count,
        total_executions=total_executions,
        passed_count=passed,
        failed_count=failed,
        error_count=errored,
        pass_rate=pass_rate,
        latency_p50_ms=statistics.median(latencies) if latencies else None,
        latency_p95_ms=statistics.quantiles(latencies, n=20)[18]
        if len(latencies) >= 20
        else None,
        latency_max_ms=max(latencies) if latencies else None,
        latency_avg_ms=statistics.mean(latencies) if latencies else None,
        total_agent_token_usage=total_agent,
        total_platform_token_usage=total_platform,
        total_agent_cost_usd=sum(agent_costs) if agent_costs else None,
        total_platform_cost_usd=sum(platform_costs) if platform_costs else None,
        total_estimated_cost_usd=total_cost_usd,
        avg_overall_score=weighted_metrics_score_pct,
        weighted_metrics_score_pct=weighted_metrics_score_pct,
        metrics_pass_threshold=metrics_pass_threshold,
        metrics_passed=metrics_passed,
        cases_pass_rate_pct=cases_pass_rate_pct,
        cases_pass_threshold=cases_pass_threshold,
        cases_passed=cases_passed,
    )


def _parse_run_agent_mode(raw: str | None) -> AgentMode:
    if not raw:
        return AgentMode.ENDPOINT
    try:
        return AgentMode(raw)
    except ValueError:
        return AgentMode.ENDPOINT


async def _execute_single_test_case(
    run_id: uuid.UUID,
    test_case: TestCase,
    agent_endpoint_url: str | None,
    config: RunConfig,
    agent_mode: AgentMode,
    agent_model: str | None,
    agent_provider: str | None,
    agent_system_prompt: str | None,
    agent_tools: list[dict[str, Any]] | None,
    semaphore: asyncio.Semaphore,
    cancel_event: asyncio.Event,
    *,
    repetition_index: int = 0,
) -> TestCaseResult:
    from sqlmodel import Session

    from app import crud
    from app.core.db import engine
    from app.models import TestCaseResultCreate, TestCaseResultUpdate
    from app.models.schemas import TestCaseProgressData
    from app.services.run_manager import run_manager

    with Session(engine) as session:
        result = crud.create_test_case_result(
            session=session,
            result_in=TestCaseResultCreate(
                run_id=run_id,
                test_case_id=test_case.id,
                repetition_index=repetition_index,
            ),
        )
        result_id = result.id

    async with semaphore:
        if cancel_event.is_set():
            return result

        run_manager.emit(
            run_id,
            "test_case_started",
            {"test_case_id": str(test_case.id), "test_case_name": test_case.name},
        )

        started_at = datetime.now(UTC)
        try:
            run_out, verdict = await run_test_case_with_evaluation(
                test_case=test_case,
                agent_endpoint_url=agent_endpoint_url,
                config=config,
                agent_mode=agent_mode,
                agent_model=agent_model,
                agent_provider=agent_provider,
                agent_system_prompt=agent_system_prompt,
                agent_tools=agent_tools,
                cancel_event=cancel_event,
            )
            transcript = run_out.transcript
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

            platform_usage = sum_platform_usage_dicts(
                run_out.platform_token_usage,
                verdict.judge_token_usage if verdict else None,
            )
            judge_cost = (verdict.judge_cost_usd or 0.0) if verdict else 0.0
            if verdict and verdict.judge_cost_usd is None:
                logger.warning(
                    "Judge cost unavailable for test_case %s — LiteLLM may lack "
                    "pricing for model %s; judge cost excluded from totals",
                    test_case.id,
                    verdict.judge_model,
                )
            platform_cost = run_out.platform_cost_usd + judge_cost
            agent_cost = run_out.agent_cost_usd
            total_cost = agent_cost + platform_cost
            agent_usage_out = (
                run_out.agent_token_usage if run_out.agent_token_usage else None
            )
            platform_usage_out = platform_usage if platform_usage else None

            update_data = TestCaseResultUpdate(
                transcript=transcript,
                turn_count=turn_count,
                verdict=verdict,
                total_latency_ms=total_latency_ms,
                agent_latency_p50_ms=p50,
                agent_latency_p95_ms=p95,
                agent_latency_max_ms=max_lat,
                agent_latency_per_turn_ms=agent_latencies or None,
                agent_token_usage=agent_usage_out,
                platform_token_usage=platform_usage_out,
                agent_cost_usd=agent_cost or None,
                platform_cost_usd=platform_cost or None,
                estimated_cost_usd=total_cost or None,
                passed=_derive_test_case_passed(verdict),
                started_at=started_at,
                completed_at=completed_at,
            )

        except Exception as e:
            logger.exception("TestCase %s failed unexpectedly", test_case.id)
            completed_at = datetime.now(UTC)
            update_data = TestCaseResultUpdate(
                passed=False,
                error_message=str(e),
                started_at=started_at,
                completed_at=completed_at,
            )

        # Persist
        db_persist_failed = False
        try:

            def _update_db():
                with Session(engine) as session:
                    db_result = crud.get_test_case_result(
                        session=session, result_id=result_id
                    )
                    if db_result:
                        return crud.update_test_case_result(
                            session=session,
                            db_result=db_result,
                            result_in=update_data,
                        )
                    return None

            updated_result = await asyncio.to_thread(_update_db)
        except Exception:
            logger.exception(
                "Failed to persist result for test_case %s in run %s",
                test_case.id,
                run_id,
            )
            db_persist_failed = True
            # Record the persistence failure on the result so it's visible
            try:

                def _mark_db_error():
                    with Session(engine) as session:
                        db_result = crud.get_test_case_result(
                            session=session, result_id=result_id
                        )
                        if db_result:
                            return crud.update_test_case_result(
                                session=session,
                                db_result=db_result,
                                result_in=TestCaseResultUpdate(
                                    passed=False,
                                    error_message="DB persistence failed for test_case result",
                                    started_at=started_at,
                                    completed_at=datetime.now(UTC),
                                ),
                            )
                        return None

                updated_result = await asyncio.to_thread(_mark_db_error)
            except Exception:
                logger.exception(
                    "Failed to mark DB error for test_case %s in run %s",
                    test_case.id,
                    run_id,
                )
                updated_result = None

        # Update progress (under lock to prevent race conditions)
        try:
            state = run_manager.get_state(run_id)
            if state:
                async with state.progress_lock:
                    progress = state.progress
                    progress.completed_count += 1
                    if updated_result is None or db_persist_failed:
                        progress.error_count += 1
                    elif updated_result.passed:
                        progress.passed_count += 1
                    elif updated_result.error_message is not None:
                        progress.error_count += 1
                    else:
                        progress.failed_count += 1

                    run_manager.emit(
                        run_id,
                        "test_case_completed",
                        TestCaseProgressData(
                            run_id=run_id,
                            test_case_id=test_case.id,
                            test_case_name=test_case.name,
                            completed_count=progress.completed_count,
                            total_count=progress.total_test_cases,
                            passed=updated_result.passed if updated_result else False,
                            overall_score=updated_result.verdict.get("overall_score")
                            if updated_result and updated_result.verdict
                            else None,
                            error_message=updated_result.error_message
                            if updated_result
                            else "DB persistence failed",
                        ).model_dump(mode="json"),
                    )
        except Exception:
            logger.exception(
                "Failed to emit progress for test_case %s in run %s",
                test_case.id,
                run_id,
            )

        return updated_result or result


async def execute_run(run_id: uuid.UUID) -> None:
    """Top-level orchestration: load run + test cases, execute concurrently, persist results."""
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

            eval_config = crud.get_eval_config(
                session=session, eval_config_id=run.eval_config_id
            )
            if not eval_config:
                logger.error("Run %s references missing eval config", run_id)
                crud.update_run(
                    session=session,
                    db_run=run,
                    run_in=RunUpdate(
                        status=RunStatus.FAILED,
                        completed_at=datetime.now(UTC),
                    ),
                )
                return

            crud.update_run(
                session=session,
                db_run=run,
                run_in=RunUpdate(
                    status=RunStatus.RUNNING, started_at=datetime.now(UTC)
                ),
            )

            execution_plan = crud.get_test_cases_for_config(
                session=session, eval_config_id=run.eval_config_id
            )

            config = RunConfig.model_validate(run.config) if run.config else RunConfig()
            agent_endpoint_url = run.agent_endpoint_url
            agent_system_prompt = run.agent_system_prompt
            agent_tools = run.agent_tools
            agent_mode = _parse_run_agent_mode(run.agent_mode)
            agent_model = run.agent_model
            agent_provider = run.agent_provider

        total_expanded = sum(entry.repetitions for entry in execution_plan)
        state.progress.total_test_cases = total_expanded
        run_manager.emit(
            run_id,
            "run_started",
            {"run_id": str(run_id), "total_test_cases": total_expanded},
        )

        semaphore = asyncio.Semaphore(config.concurrency)
        tasks = [
            _execute_single_test_case(
                run_id=run_id,
                test_case=entry.test_case,
                agent_endpoint_url=agent_endpoint_url,
                config=config,
                agent_mode=agent_mode,
                agent_model=agent_model,
                agent_provider=agent_provider,
                agent_system_prompt=agent_system_prompt,
                agent_tools=agent_tools,
                semaphore=semaphore,
                cancel_event=state.cancel_event,
                repetition_index=rep,
            )
            for entry in execution_plan
            for rep in range(entry.repetitions)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results: list[TestCaseResult] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.exception(
                    "TestCase task %d failed for run %s: %s",
                    i,
                    run_id,
                    r,
                    exc_info=r,
                )
            else:
                valid_results.append(r)

        aggregate_metrics = compute_aggregate_metrics(
            valid_results,
            metrics_pass_threshold=config.metrics_pass_threshold,
            cases_pass_threshold=config.cases_pass_threshold,
        )

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
