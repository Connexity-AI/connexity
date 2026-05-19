"""Retell text runtime.

Connexity owns the user simulator and judge. Retell owns the tested agent side
through the stateless playground API: one initial empty-history request per
test-case execution, then one full-history ``agent-playground-completion``
request per simulated user turn.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, replace
from typing import Any, ClassVar

from sqlmodel import Session

from app.core.encryption import decrypt
from app.models.agent import Agent
from app.models.enums import (
    AgentMode,
    FirstTurn,
    Platform,
    RunMode,
    TextRuntimeKind,
    TurnRole,
)
from app.models.integration import Integration
from app.models.schemas import (
    ConversationTurn,
    RetellRuntimeConfig,
    RuntimeConfig,
    ToolCall,
    ToolCallFunction,
    UserSimulatorConfig,
)
from app.models.test_case import TestCase
from app.services.cost_tracker import TestCaseTokenAccumulator
from app.services.eval_runtimes.base import RuntimeRunArgs, RuntimeTestResult
from app.services.eval_runtimes.text.base import (
    TextAgentTurnConfig,
    TextAgentTurnContext,
    TextRuntimeBase,
)
from app.services.eval_runtimes.types import TestCaseRunResult
from app.services.retell import (
    RetellAgentPlaygroundCompletionResult,
    RetellChatMessage,
    create_retell_agent_playground_completion,
)
from app.services.user_simulator import UserSimulator

logger = logging.getLogger(__name__)


@dataclass
class RetellPlaygroundState:
    dynamic_variables: dict[str, Any] = field(default_factory=dict)
    current_state: str | None = None
    current_node_id: str | None = None
    component_id: str | None = None
    call_ended: bool = False


@dataclass(frozen=True)
class RetellTextAgentConfig(TextAgentTurnConfig):
    api_key: str = ""
    retell_agent_id: str = ""
    playground_state: RetellPlaygroundState = field(
        default_factory=RetellPlaygroundState
    )


class RetellRuntime(TextRuntimeBase):
    MODE: ClassVar[RunMode] = RunMode.TEXT
    KIND: ClassVar[TextRuntimeKind] = TextRuntimeKind.RETELL
    LABEL: ClassVar[str] = "Retell"
    DESCRIPTION: ClassVar[str] = "Run evaluations using Retell"

    def supported_for_platform(self, platform: Platform | None) -> bool:
        return platform == Platform.RETELL

    def validate_config(
        self,
        runtime_config: RuntimeConfig,
        agent: Agent,
        session: Session,
    ) -> None:
        if not isinstance(runtime_config, RetellRuntimeConfig):
            msg = "retell runtime requires a RetellRuntimeConfig"
            raise ValueError(msg)
        if agent.platform != Platform.RETELL:
            msg = "Retell runtime requires a Retell agent."
            raise ValueError(msg)
        if agent.integration_id is None or agent.platform_agent_id is None:
            msg = "Retell runtime requires an integration and platform agent id."
            raise ValueError(msg)

    async def test_connection(
        self,
        runtime_config: RuntimeConfig,
        agent: Agent,
        session: Session,
    ) -> RuntimeTestResult:
        try:
            self.validate_config(runtime_config, agent, session)
        except ValueError as exc:
            return RuntimeTestResult(ok=False, message=str(exc))

        integration = session.get(Integration, agent.integration_id)
        if integration is None:
            return RuntimeTestResult(ok=False, message="Retell integration not found.")

        try:
            api_key = decrypt(integration.encrypted_api_key)
        except Exception as exc:
            return RuntimeTestResult(
                ok=False, message=f"Could not decrypt Retell API key: {exc}"
            )

        result = await create_retell_agent_playground_completion(
            api_key=api_key,
            retell_agent_id=agent.platform_agent_id or "",
            messages=[],
        )
        if not result.success:
            return RuntimeTestResult(
                ok=False,
                message=result.error_message
                or "Retell playground request failed.",
            )

        return RuntimeTestResult(
            ok=True,
            message="Retell playground is reachable.",
        )

    def build_text_agent_config(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TextAgentTurnConfig:
        if not isinstance(runtime_config, RetellRuntimeConfig):
            msg = "retell runtime requires a RetellRuntimeConfig"
            raise ValueError(msg)

        integration_id = args.agent_snapshot.integration_id
        if integration_id is None:
            msg = "Retell runtime requires an integration id on the run snapshot."
            raise ValueError(msg)
        integration = session.get(Integration, integration_id)
        if integration is None:
            msg = "Retell integration not found."
            raise ValueError(msg)

        try:
            api_key = decrypt(integration.encrypted_api_key)
        except Exception as exc:
            msg = f"Could not decrypt Retell API key: {exc}"
            raise ValueError(msg) from exc

        retell_agent_id = (args.agent_snapshot.platform_agent_id or "").strip()
        if not retell_agent_id:
            msg = "Retell runtime requires a platform agent id on the run snapshot."
            raise ValueError(msg)

        return RetellTextAgentConfig(
            endpoint_url=None,
            agent_mode=AgentMode.PLATFORM,
            model=args.agent_snapshot.model,
            provider=args.agent_snapshot.provider,
            system_prompt=args.agent_snapshot.system_prompt,
            tools=args.agent_snapshot.tools,
            api_key=api_key,
            retell_agent_id=retell_agent_id,
        )

    async def run_test_case(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TestCaseRunResult:
        base_agent_config = self.build_text_agent_config(runtime_config, args, session)
        assert isinstance(base_agent_config, RetellTextAgentConfig)

        agent_config = replace(
            base_agent_config,
            playground_state=RetellPlaygroundState(
                dynamic_variables=self._dynamic_variables_for_test_case(args.test_case)
            ),
        )

        transcript: list[ConversationTurn] = []
        accumulator = TestCaseTokenAccumulator()
        initial_result = await create_retell_agent_playground_completion(
            api_key=agent_config.api_key,
            retell_agent_id=agent_config.retell_agent_id,
            messages=[],
            dynamic_variables=agent_config.playground_state.dynamic_variables or None,
        )
        if not initial_result.success:
            transcript.append(
                self.build_conversation_turn(
                    index=0,
                    role=TurnRole.ASSISTANT,
                    content=(
                        "[agent_error] "
                        f"{initial_result.error_message or 'Retell playground setup failed'}"
                    ),
                )
            )
            return self._build_result(transcript, accumulator)

        self._apply_retell_playground_result(
            agent_config.playground_state, initial_result
        )
        return await self._run_retell_text_case(
            test_case=args.test_case,
            agent_config=agent_config,
            config=args.run_snapshot.run_config,
            initial_messages=initial_result.messages,
            initial_latency_ms=initial_result.latency_ms,
            cancel_event=args.run_snapshot.cancel_event,
        )

    async def _run_retell_text_case(
        self,
        *,
        test_case: TestCase,
        agent_config: RetellTextAgentConfig,
        config,
        initial_messages: list[RetellChatMessage],
        initial_latency_ms: int | None,
        cancel_event: asyncio.Event | None,
    ) -> TestCaseRunResult:
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

        opening_agent_turn = self._append_retell_messages_to_transcript(
            transcript,
            initial_messages,
            initial_latency_ms,
        )
        if self._turns_have_terminating_assistant_tool_call(
            transcript, agent_config.tools
        ):
            return self._build_result(transcript, accumulator)
        if agent_config.playground_state.call_ended:
            return self._build_result(transcript, accumulator)

        if first_turn == FirstTurn.USER:
            if first_message_text:
                transcript.append(
                    self.build_conversation_turn(
                        index=len(transcript),
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
                        index=len(transcript),
                        role=TurnRole.USER,
                        content=opening.content,
                        latency_ms=opening.latency_ms,
                        token_count=total_tokens,
                    )
                )
        elif not opening_agent_turn and first_message_text:
            transcript.append(
                self.build_conversation_turn(
                    index=len(transcript),
                    role=TurnRole.ASSISTANT,
                    content=first_message_text,
                )
            )
        elif not opening_agent_turn:
            transcript.append(
                self.build_conversation_turn(
                    index=len(transcript),
                    role=TurnRole.ASSISTANT,
                    content=(
                        "[agent_error] Retell playground did not provide an "
                        "opening agent message for an agent-first test case"
                    ),
                )
            )
            return self._build_result(transcript, accumulator)

        max_agent_rounds = config.max_turns
        agent_rounds = 1 if opening_agent_turn else 0
        if (
            not opening_agent_turn
            and first_turn == FirstTurn.AGENT
            and first_message_text
        ):
            agent_rounds = 1

        started = time.perf_counter()
        timeout_ms = config.timeout_per_test_case_ms

        while True:
            if cancel_event is not None and cancel_event.is_set():
                logger.warning("TestCase %s stopped: run cancelled", test_case.id)
                transcript.append(
                    self.build_conversation_turn(
                        index=len(transcript),
                        role=TurnRole.ASSISTANT,
                        content="[platform: run cancelled]",
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
                    )
                )
                if not ok:
                    break
                if self._turns_have_terminating_assistant_tool_call(
                    transcript[turn_before:], agent_config.tools
                ):
                    break
                agent_rounds += 1
                if agent_config.playground_state.call_ended:
                    break

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
                    )
                )
                if not ok:
                    break
                if self._turns_have_terminating_assistant_tool_call(
                    transcript[turn_before:], agent_config.tools
                ):
                    break
                agent_rounds += 1
                if agent_config.playground_state.call_ended:
                    break

        return self._build_result(transcript, accumulator)

    async def do_agent_turn(self, context: TextAgentTurnContext) -> bool:
        agent_config = context.agent_config
        assert isinstance(agent_config, RetellTextAgentConfig)

        if not context.transcript or context.transcript[-1].role != TurnRole.USER:
            context.transcript.append(
                self.build_conversation_turn(
                    index=len(context.transcript),
                    role=TurnRole.ASSISTANT,
                    content=(
                        "[agent_error] Retell playground requires the latest "
                        "transcript turn to be a user message"
                    ),
                )
            )
            return False

        user_content = (context.transcript[-1].content or "").strip()
        if not user_content:
            context.transcript.append(
                self.build_conversation_turn(
                    index=len(context.transcript),
                    role=TurnRole.ASSISTANT,
                    content="[agent_error] latest user message is empty",
                )
            )
            return False

        result = await create_retell_agent_playground_completion(
            api_key=agent_config.api_key,
            retell_agent_id=agent_config.retell_agent_id,
            messages=self._transcript_to_retell_playground_messages(
                context.transcript
            ),
            dynamic_variables=agent_config.playground_state.dynamic_variables or None,
            current_state=agent_config.playground_state.current_state,
            current_node_id=agent_config.playground_state.current_node_id,
            component_id=agent_config.playground_state.component_id,
        )
        if not result.success:
            logger.warning(
                "Retell agent-playground-completion failed for test_case %s: %s",
                context.test_case.id,
                result.error_message,
            )
            context.transcript.append(
                self.build_conversation_turn(
                    index=len(context.transcript),
                    role=TurnRole.ASSISTANT,
                    content=f"[agent_error] {result.error_message or 'Retell chat failed'}",
                )
            )
            return False

        self._apply_retell_playground_result(
            agent_config.playground_state, result
        )
        if not result.messages:
            if agent_config.playground_state.call_ended:
                return True
            context.transcript.append(
                self.build_conversation_turn(
                    index=len(context.transcript),
                    role=TurnRole.ASSISTANT,
                    content="[agent_error] Retell returned no messages",
                )
            )
            return False

        self._append_retell_messages_to_transcript(
            context.transcript,
            result.messages,
            result.latency_ms,
        )
        return True

    @staticmethod
    def _dynamic_variables_for_test_case(test_case: TestCase) -> dict[str, Any]:
        raw = test_case.user_context or {}
        out: dict[str, Any] = {}
        for key, value in raw.items():
            if value is None:
                continue
            if isinstance(value, str):
                out[key] = value
            elif isinstance(value, int | float | bool):
                out[key] = str(value)
            else:
                out[key] = json.dumps(value, ensure_ascii=False)
        return out

    def _append_retell_messages_to_transcript(
        self,
        transcript: list[ConversationTurn],
        messages: list[RetellChatMessage],
        round_latency_ms: int | None,
    ) -> bool:
        appended_agent_turn = False
        last_message_index = len(messages) - 1
        for message_index, message in enumerate(messages):
            latency_ms = (
                round_latency_ms if message_index == last_message_index else None
            )
            role = message.role.strip().lower()
            if role == "agent":
                transcript.append(
                    self.build_conversation_turn(
                        index=len(transcript),
                        role=TurnRole.ASSISTANT,
                        content=message.content,
                        latency_ms=latency_ms,
                    )
                )
                appended_agent_turn = True
                continue
            if role == "user":
                transcript.append(
                    self.build_conversation_turn(
                        index=len(transcript),
                        role=TurnRole.USER,
                        content=message.content,
                        latency_ms=latency_ms,
                    )
                )
                continue
            if role == "tool_call_invocation":
                tool_call_id = message.tool_call_id or f"retell_call_{len(transcript)}"
                transcript.append(
                    self.build_conversation_turn(
                        index=len(transcript),
                        role=TurnRole.ASSISTANT,
                        content=None,
                        latency_ms=latency_ms,
                        tool_calls=[
                            ToolCall(
                                id=tool_call_id,
                                function=ToolCallFunction(
                                    name=message.name or "unknown_tool",
                                    arguments=message.arguments or "{}",
                                ),
                            )
                        ],
                    )
                )
                appended_agent_turn = True
                continue
            if role == "tool_call_result":
                transcript.append(
                    self.build_conversation_turn(
                        index=len(transcript),
                        role=TurnRole.TOOL,
                        content=message.content,
                        latency_ms=latency_ms,
                        tool_call_id=message.tool_call_id,
                    )
                )
                continue

            transcript.append(
                self.build_conversation_turn(
                    index=len(transcript),
                    role=TurnRole.ASSISTANT,
                    content=message.content or f"[retell:{message.role}]",
                    latency_ms=latency_ms,
                )
            )
            appended_agent_turn = True

        return appended_agent_turn

    @staticmethod
    def _apply_retell_playground_result(
        state: RetellPlaygroundState,
        result: RetellAgentPlaygroundCompletionResult,
    ) -> None:
        state.dynamic_variables = dict(result.dynamic_variables)
        if result.current_state is not None:
            state.current_state = result.current_state
        if result.current_node_id is not None:
            state.current_node_id = result.current_node_id
        state.call_ended = result.call_ended

    @staticmethod
    def _transcript_to_retell_playground_messages(
        transcript: list[ConversationTurn],
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for turn in transcript:
            if turn.role == TurnRole.USER:
                messages.append(
                    {"role": "user", "content": (turn.content or "").strip()}
                )
                continue
            if turn.role == TurnRole.ASSISTANT:
                if turn.content is not None:
                    messages.append({"role": "agent", "content": turn.content})
                for tool_call in turn.tool_calls or []:
                    messages.append(
                        {
                            "role": "tool_call_invocation",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        }
                    )
                continue
            if turn.role == TurnRole.TOOL:
                messages.append(
                    {
                        "role": "tool_call_result",
                        "tool_call_id": turn.tool_call_id,
                        "content": turn.content,
                    }
                )
        return messages
