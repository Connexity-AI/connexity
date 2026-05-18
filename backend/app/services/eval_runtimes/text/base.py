"""Shared conversation loop for text runtimes.

This module owns only the runtime-agnostic loop: user simulator turns, turn
ordering, cancellation, timeout handling, terminating-tool detection, and result
assembly. Concrete runtimes own the agent turn.
"""

import asyncio
import logging
import time
import uuid
from abc import abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from sqlmodel import Session

from app.models.agent_contract import AgentResponse, ChatMessage
from app.models.enums import AgentMode, FirstTurn, SimulatorMode, TurnRole
from app.models.schemas import (
    ConversationTurn,
    RunConfig,
    RuntimeConfig,
    ToolCall,
    UserSimulatorConfig,
)
from app.models.test_case import TestCase
from app.services.agent_tool_definitions import snapshot_marks_tool_terminating
from app.services.cost_tracker import TestCaseTokenAccumulator
from app.services.eval_runtimes.base import EvalRuntime, RuntimeRunArgs
from app.services.eval_runtimes.types import TestCaseRunResult
from app.services.llm import LLMMessage
from app.services.user_simulator import UserSimulator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TextAgentTurnConfig:
    """Agent-turn configuration resolved by a concrete text runtime."""

    endpoint_url: str | None
    agent_mode: AgentMode = AgentMode.ENDPOINT
    model: str | None = None
    provider: str | None = None
    system_prompt: str | None = None
    tools: list[dict[str, Any]] | None = None
    platform_tool_executor_mode: Literal["mock", "live", "synthetic"] | None = None


@dataclass
class TextAgentTurnContext:
    """Mutable state available while a runtime executes one agent turn."""

    transcript: list[ConversationTurn]
    test_case: TestCase
    run_config: RunConfig
    agent_config: TextAgentTurnConfig
    accumulator: TestCaseTokenAccumulator
    timeout_ms: int
    started: float
    run_id: uuid.UUID | None = None
    repetition_index: int = 0

    @property
    def remaining_ms(self) -> int:
        elapsed_ms = int((time.perf_counter() - self.started) * 1000)
        return max(1, self.timeout_ms - elapsed_ms)


class TextRuntimeBase(EvalRuntime):
    """Base class for text runtimes driven by Connexity's user simulator."""

    @staticmethod
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

    @staticmethod
    def transcript_to_agent_messages(
        transcript: list[ConversationTurn],
    ) -> list[ChatMessage]:
        """Map stored turns to the agent wire format (roles unchanged)."""
        return [
            ChatMessage(
                role=turn.role,
                content=turn.content,
                tool_calls=turn.tool_calls,
                tool_call_id=turn.tool_call_id,
                name=None,
            )
            for turn in transcript
        ]

    @staticmethod
    def transcript_to_simulator_messages(
        transcript: list[ConversationTurn],
    ) -> list[LLMMessage]:
        """User/assistant text turns only, roles flipped for the simulator LLM."""
        out: list[LLMMessage] = []
        for turn in transcript:
            if turn.role in (TurnRole.SYSTEM, TurnRole.TOOL):
                continue
            if turn.role == TurnRole.USER:
                text = (turn.content or "").strip()
                if text:
                    out.append(LLMMessage(role="assistant", content=text))
                continue
            if turn.role == TurnRole.ASSISTANT:
                text = (turn.content or "").strip()
                if turn.tool_calls and not text:
                    text = "[Assistant requested tool calls]"
                if text:
                    out.append(LLMMessage(role="user", content=text))
        return out

    @staticmethod
    def _turns_have_terminating_assistant_tool_call(
        turns: list[ConversationTurn],
        agent_tools: list[dict[str, Any]] | None,
    ) -> bool:
        """True if any assistant turn requests a tool marked terminating on the snapshot."""
        if not agent_tools:
            return False
        for turn in turns:
            if turn.role != TurnRole.ASSISTANT or not turn.tool_calls:
                continue
            for tool_call in turn.tool_calls:
                if snapshot_marks_tool_terminating(
                    tool_call.function.name, agent_tools
                ):
                    return True
        return False

    @staticmethod
    async def _do_user_turn(
        transcript: list[ConversationTurn],
        simulator: UserSimulator,
        sim_cfg: UserSimulatorConfig,
        accumulator: TestCaseTokenAccumulator,
    ) -> bool:
        """Execute one user simulator turn. Returns False if the loop should break."""
        if sim_cfg.mode == SimulatorMode.SCRIPTED and simulator.is_exhausted:
            return False

        try:
            sim_messages = TextRuntimeBase.transcript_to_simulator_messages(transcript)
            sim_result = await simulator.generate_message(sim_messages)
        except RuntimeError as exc:
            logger.warning("Simulator exhausted or failed: %s", exc)
            return False

        if sim_result.token_usage:
            accumulator.add_platform_usage(dict(sim_result.token_usage))
        accumulator.add_platform_cost(sim_result.cost_usd)
        total_tokens = sim_result.token_usage.get("total_tokens")
        transcript.append(
            TextRuntimeBase.build_conversation_turn(
                index=len(transcript),
                role=TurnRole.USER,
                content=sim_result.content,
                latency_ms=sim_result.latency_ms,
                token_count=total_tokens,
            )
        )

        if sim_cfg.mode == SimulatorMode.SCRIPTED and simulator.is_exhausted:
            return False

        return True

    @staticmethod
    def _build_result(
        transcript: list[ConversationTurn],
        accumulator: TestCaseTokenAccumulator,
    ) -> TestCaseRunResult:
        return TestCaseRunResult(
            transcript=transcript,
            agent_token_usage=accumulator.agent_token_usage,
            platform_token_usage=accumulator.platform_token_usage,
            agent_cost_usd=accumulator.agent_cost_usd,
            platform_cost_usd=accumulator.platform_cost_usd,
        )

    @staticmethod
    def append_wire_messages_to_transcript(
        transcript: list[ConversationTurn],
        response: AgentResponse,
        round_latency_ms: int,
    ) -> None:
        messages = response.messages
        if not messages:
            return
        last_index = len(messages) - 1
        total_tokens = response.usage.total_tokens if response.usage else None
        for message_index, message in enumerate(messages):
            transcript.append(
                TextRuntimeBase.build_conversation_turn(
                    index=len(transcript),
                    role=message.role,
                    content=message.content,
                    latency_ms=round_latency_ms
                    if message_index == last_index
                    else None,
                    tool_calls=message.tool_calls,
                    tool_call_id=message.tool_call_id,
                    token_count=total_tokens if message_index == last_index else None,
                )
            )

    @abstractmethod
    def build_text_agent_config(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TextAgentTurnConfig:
        """Return the concrete runtime's agent-turn configuration."""
        raise NotImplementedError

    async def run_test_case(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TestCaseRunResult:
        agent_config = self.build_text_agent_config(runtime_config, args, session)
        return await self.run_text_test_case(
            args.test_case,
            agent_config,
            args.run_snapshot.run_config,
            cancel_event=args.run_snapshot.cancel_event,
            run_id=args.run_snapshot.run_id,
            repetition_index=args.repetition_index,
        )

    async def run_text_test_case(
        self,
        test_case: TestCase,
        agent_config: TextAgentTurnConfig,
        config: RunConfig,
        *,
        cancel_event: asyncio.Event | None = None,
        run_id: uuid.UUID | None = None,
        repetition_index: int = 0,
    ) -> TestCaseRunResult:
        """Execute one test case using the shared text conversation loop."""
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

        accumulator = TestCaseTokenAccumulator()
        transcript: list[ConversationTurn] = []

        if first_turn == FirstTurn.USER:
            if first_message_text:
                transcript.append(
                    self.build_conversation_turn(
                        index=0,
                        role=TurnRole.USER,
                        content=simulator.get_initial_message(),
                    )
                )
            else:
                try:
                    opening = await simulator.generate_message([])
                except RuntimeError as exc:
                    logger.warning(
                        "Could not produce opening user message for test_case %s: %s",
                        test_case.id,
                        exc,
                    )
                    return self._build_result(transcript, accumulator)
                if opening.token_usage:
                    accumulator.add_platform_usage(dict(opening.token_usage))
                accumulator.add_platform_cost(opening.cost_usd)
                total_tokens = opening.token_usage.get("total_tokens")
                transcript.append(
                    self.build_conversation_turn(
                        index=0,
                        role=TurnRole.USER,
                        content=opening.content,
                        latency_ms=opening.latency_ms,
                        token_count=total_tokens,
                    )
                )
        elif first_message_text:
            transcript.append(
                self.build_conversation_turn(
                    index=0,
                    role=TurnRole.ASSISTANT,
                    content=first_message_text,
                )
            )

        max_agent_rounds = config.max_turns
        agent_rounds = 1 if first_turn == FirstTurn.AGENT and first_message_text else 0
        started = time.perf_counter()
        timeout_ms = config.timeout_per_test_case_ms

        if first_turn == FirstTurn.AGENT and not first_message_text:
            turn_before = len(transcript)
            ok = await self.do_agent_turn(
                TextAgentTurnContext(
                    transcript=transcript,
                    test_case=test_case,
                    run_config=config,
                    agent_config=agent_config,
                    accumulator=accumulator,
                    timeout_ms=timeout_ms,
                    started=started,
                    run_id=run_id,
                    repetition_index=repetition_index,
                )
            )
            if not ok:
                return self._build_result(transcript, accumulator)
            if self._turns_have_terminating_assistant_tool_call(
                transcript[turn_before:], agent_config.tools
            ):
                return self._build_result(transcript, accumulator)
            agent_rounds += 1

        while True:
            if cancel_event is not None and cancel_event.is_set():
                logger.warning("TestCase %s stopped: run cancelled", test_case.id)
                transcript.append(
                    self.build_conversation_turn(
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
                    self.build_conversation_turn(
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
                turn_before = len(transcript)
                ok = await self.do_agent_turn(
                    TextAgentTurnContext(
                        transcript=transcript,
                        test_case=test_case,
                        run_config=config,
                        agent_config=agent_config,
                        accumulator=accumulator,
                        timeout_ms=timeout_ms,
                        started=started,
                        run_id=run_id,
                        repetition_index=repetition_index,
                    )
                )
                if not ok:
                    break
                if self._turns_have_terminating_assistant_tool_call(
                    transcript[turn_before:], agent_config.tools
                ):
                    break
                agent_rounds += 1

                if max_agent_rounds is not None and agent_rounds >= max_agent_rounds:
                    break

                ok = await self._do_user_turn(
                    transcript, simulator, sim_cfg, accumulator
                )
                if not ok:
                    break
            else:
                ok = await self._do_user_turn(
                    transcript, simulator, sim_cfg, accumulator
                )
                if not ok:
                    break

                if max_agent_rounds is not None and agent_rounds >= max_agent_rounds:
                    break

                turn_before = len(transcript)
                ok = await self.do_agent_turn(
                    TextAgentTurnContext(
                        transcript=transcript,
                        test_case=test_case,
                        run_config=config,
                        agent_config=agent_config,
                        accumulator=accumulator,
                        timeout_ms=timeout_ms,
                        started=started,
                        run_id=run_id,
                        repetition_index=repetition_index,
                    )
                )
                if not ok:
                    break
                if self._turns_have_terminating_assistant_tool_call(
                    transcript[turn_before:], agent_config.tools
                ):
                    break
                agent_rounds += 1

        return self._build_result(transcript, accumulator)

    @abstractmethod
    async def do_agent_turn(self, context: TextAgentTurnContext) -> bool:
        """Execute one runtime-specific agent turn. Return False to stop."""
        raise NotImplementedError
