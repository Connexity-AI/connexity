"""Single-turn LLM agent with tool calls for test case create/edit."""

from dataclasses import dataclass
from typing import ClassVar

from app.core.config import settings
from app.models.test_case import TestCaseCreate
from app.services.llm import LLMCallConfig, LLMMessage, LLMSettingsView, call_llm
from app.services.test_case_generator.agent.context import AgentContext
from app.services.test_case_generator.agent.prompt import build_agent_messages
from app.services.test_case_generator.agent.schemas import AgentMode
from app.services.test_case_generator.agent.tools import (
    CREATE_TEST_CASE_TOOL,
    EDIT_TEST_CASE_TOOL,
    parse_create_test_case_tool_calls,
    parse_edit_test_case_tool_call,
)


@dataclass(frozen=True)
class TestCaseAgentInput:
    # Prevent pytest from collecting this dataclass as a test class.
    __test__: ClassVar[bool] = False

    mode: AgentMode
    user_message: str
    context: AgentContext
    llm_provider: str | None = None
    llm_model: str | None = None
    temperature: float | None = None


@dataclass
class TestCaseAgentOutput:
    __test__: ClassVar[bool] = False

    mode: AgentMode
    created: list[TestCaseCreate]
    edited: TestCaseCreate | None
    model_used: str
    latency_ms: int
    token_usage: dict[str, int] | None
    cost_usd: float | None


class TestCaseAgent:
    """Runs one non-streaming LLM call with tools and parses results."""

    __test__ = False

    def __init__(self, inp: TestCaseAgentInput) -> None:
        self._inp = inp

    async def run(
        self, *, app_settings: LLMSettingsView | None = None
    ) -> TestCaseAgentOutput:
        static, dynamic, user_content = build_agent_messages(
            mode=self._inp.mode,
            user_message=self._inp.user_message,
            ctx=self._inp.context,
        )
        messages = [
            LLMMessage(role="system", content=static),
            LLMMessage(role="system", content=dynamic),
            LLMMessage(role="user", content=user_content),
        ]

        tools = (
            [CREATE_TEST_CASE_TOOL]
            if self._inp.mode in (AgentMode.CREATE, AgentMode.FROM_TRANSCRIPT)
            else [EDIT_TEST_CASE_TOOL]
        )

        temperature = (
            self._inp.temperature
            if self._inp.temperature is not None
            else settings.GENERATOR_TEMPERATURE
        )

        llm_config = LLMCallConfig(
            model=self._inp.llm_model,
            provider=self._inp.llm_provider,
            max_tokens=settings.GENERATOR_MAX_TOKENS,
            temperature=temperature,
            tools=tools,
            parallel_tool_calls=True,
            extra={"tool_choice": "required"},
        )

        response = await call_llm(
            messages,
            llm_config,
            app_settings=app_settings,
        )

        raw_calls = response.tool_calls
        created: list[TestCaseCreate] = []
        edited: TestCaseCreate | None = None

        if self._inp.mode in (AgentMode.CREATE, AgentMode.FROM_TRANSCRIPT):
            created = parse_create_test_case_tool_calls(raw_calls)
            if not created:
                msg = "LLM returned no valid create_test_case tool calls"
                raise ValueError(msg)
            if self._inp.mode == AgentMode.FROM_TRANSCRIPT and len(created) != 1:
                msg = (
                    f"from_transcript mode expects exactly one create_test_case; "
                    f"got {len(created)}"
                )
                raise ValueError(msg)
        else:
            edited = parse_edit_test_case_tool_call(raw_calls)
            if edited is None:
                msg = "LLM returned no valid edit_test_case tool call"
                raise ValueError(msg)

        return TestCaseAgentOutput(
            mode=self._inp.mode,
            created=created,
            edited=edited,
            model_used=response.model,
            latency_ms=response.latency_ms or 0,
            token_usage=dict(response.usage) if response.usage else None,
            cost_usd=response.response_cost_usd,
        )
