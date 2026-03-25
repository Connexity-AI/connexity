"""Partial run orchestration: agent HTTP calls, message mapping, scenario loop."""

import logging
import time
from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from app.models.agent_contract import (
    AgentRequest,
    AgentRequestMetadata,
    AgentResponse,
    ChatMessage,
)
from app.models.enums import TurnRole
from app.models.scenario import Scenario
from app.models.schemas import ConversationTurn, Persona, RunConfig, ToolCall
from app.services.llm import LLMMessage
from app.services.user_simulator import SimulatorConfig, SimulatorMode, UserSimulator

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
    simulator_config: SimulatorConfig | None = None,
) -> list[ConversationTurn]:
    """Execute one scenario: initial user message, then agent / simulator turns.

    If ``scenario.initial_message`` is empty, the opening user line is produced by
    calling the simulator (LLM mode: first completion; scripted mode: first
    scripted line).

    Stops when ``scenario.max_turns`` agent rounds are done, scripted lines are
    exhausted, timeout is hit, or the agent call fails.
    """
    sim_cfg = simulator_config or SimulatorConfig(
        mode=SimulatorMode.LLM,
        model=config.simulator_model,
        provider=config.simulator_provider,
    )
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
