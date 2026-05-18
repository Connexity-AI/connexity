"""Connexity text runtime.

In-process **user simulator** plus **platform-side agent inference** via
:class:`~app.services.agent_simulator.AgentSimulator`. No HTTP calls to an
external agent endpoint — use :class:`CustomEndpointRuntime` for that.

Judging is performed by the orchestrator.
"""

import logging
from typing import ClassVar

from sqlmodel import Session

from app.core.config import settings
from app.models.agent import Agent
from app.models.agent_contract import AgentResponse, TokenUsage
from app.models.enums import AgentMode, Platform, RunMode, TextRuntimeKind, TurnRole
from app.models.schemas import ConnexityRuntimeConfig, RuntimeConfig
from app.services.agent_simulator import AgentSimulator
from app.services.eval_runtimes.base import RuntimeRunArgs, RuntimeTestResult
from app.services.eval_runtimes.text.base import (
    TextAgentTurnConfig,
    TextAgentTurnContext,
    TextRuntimeBase,
)
from app.services.tool_dispatch import build_tool_executor

logger = logging.getLogger(__name__)


class ConnexityRuntime(TextRuntimeBase):
    MODE: ClassVar[RunMode] = RunMode.TEXT
    KIND: ClassVar[TextRuntimeKind] = TextRuntimeKind.CONNEXITY
    LABEL: ClassVar[str] = "Connexity"
    DESCRIPTION: ClassVar[str] = "Run evaluations using Connexity"

    def supported_for_platform(self, platform: Platform | None) -> bool:
        return True

    def validate_config(
        self,
        runtime_config: RuntimeConfig,
        agent: Agent,
        session: Session,
    ) -> None:
        if not isinstance(runtime_config, ConnexityRuntimeConfig):
            msg = "connexity runtime requires a ConnexityRuntimeConfig"
            raise ValueError(msg)
        sp = (agent.system_prompt or "").strip()
        if not sp:
            msg = (
                "Connexity runtime needs a non-empty system_prompt on the agent "
                "(or use the custom_endpoint runtime for HTTP agents)."
            )
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
        return RuntimeTestResult(
            ok=True, message="Connexity runtime is always available."
        )

    def build_text_agent_config(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TextAgentTurnConfig:
        if not isinstance(runtime_config, ConnexityRuntimeConfig):
            msg = "connexity runtime requires a ConnexityRuntimeConfig"
            raise ValueError(msg)
        agent = args.agent_snapshot
        return TextAgentTurnConfig(
            endpoint_url=None,
            agent_mode=AgentMode.PLATFORM,
            model=agent.model,
            provider=agent.provider,
            system_prompt=agent.system_prompt,
            tools=agent.tools,
        )

    async def do_agent_turn(self, context: TextAgentTurnContext) -> bool:
        agent_messages = self.transcript_to_agent_messages(context.transcript)
        simulator = self._make_agent_simulator(context)
        logger.info(
            "Connexity runtime request: run_id=%s test_case_id=%s repetition_index=%s transcript_turns=%s model=%s provider=%s tool_mode=%s",
            context.run_id,
            context.test_case.id,
            context.repetition_index,
            len(context.transcript),
            context.agent_config.model,
            context.agent_config.provider,
            context.run_config.tool_mode,
        )
        try:
            platform_result = await simulator.generate_response(agent_messages)
        except Exception as exc:
            logger.warning(
                "AgentSimulator failed for test_case %s: %s",
                context.test_case.id,
                exc,
            )
            context.transcript.append(
                self.build_conversation_turn(
                    index=len(context.transcript),
                    role=TurnRole.ASSISTANT,
                    content=f"[agent_error] {exc!s}",
                    latency_ms=None,
                )
            )
            return False

        usage_map = platform_result.token_usage
        if usage_map:
            context.accumulator.add_agent_usage(usage_map)
        if platform_result.cost_usd is not None:
            context.accumulator.add_agent_cost(platform_result.cost_usd)

        wire = AgentResponse(
            messages=platform_result.messages,
            model=platform_result.model,
            provider=platform_result.provider,
            usage=TokenUsage(
                prompt_tokens=usage_map.get("prompt_tokens"),
                completion_tokens=usage_map.get("completion_tokens"),
                total_tokens=usage_map.get("total_tokens"),
            ),
        )
        self.append_wire_messages_to_transcript(
            context.transcript, wire, platform_result.latency_ms
        )
        return True

    def _make_agent_simulator(self, context: TextAgentTurnContext) -> AgentSimulator:
        model_id = (context.agent_config.model or "").strip()
        if not model_id:
            logger.error(
                "Platform agent requires agent_model on the run snapshot; test_case %s",
                context.test_case.id,
            )
        effective_tool_mode = (
            context.agent_config.platform_tool_executor_mode
            if context.agent_config.platform_tool_executor_mode is not None
            else context.run_config.tool_mode
        )
        tool_executor = build_tool_executor(
            tools=context.agent_config.tools,
            expected_tool_calls=context.test_case.expected_tool_calls,
            test_case_context=context.test_case.user_context or {},
            tool_mode=effective_tool_mode,
        )
        return AgentSimulator(
            system_prompt=context.agent_config.system_prompt or "",
            tools=context.agent_config.tools,
            agent_model=model_id or settings.default_llm_id,
            agent_provider=context.agent_config.provider,
            config=context.run_config.agent_simulator,
            tool_executor=tool_executor,
        )
