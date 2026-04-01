"""LLM- and scripted-mode user simulator for eval conversations."""

import json

from pydantic import BaseModel, Field

from app.models.enums import SimulatorMode
from app.models.schemas import Persona, UserSimulatorConfig
from app.services.llm import LLMCallConfig, LLMMessage, call_llm


class SimulatorResult(BaseModel):
    """One simulated user utterance and timing."""

    content: str = Field(description="The user message text")
    latency_ms: int | None = Field(
        default=None,
        description="Latency of generation (LLM) or 0 for scripted",
    )
    token_usage: dict[str, int] = Field(
        default_factory=dict,
        description="Token usage from the simulator LLM call, if any",
    )
    cost_usd: float | None = Field(
        default=None,
        description="LiteLLM-estimated USD cost for the simulator completion, if any",
    )


def _build_system_prompt(
    persona: Persona,
    user_context: dict[str, object] | None,
    expected_outcomes: dict[str, object] | None,
) -> str:
    """Build the simulator system prompt from persona and scenario context."""
    ctx_block = (
        json.dumps(user_context, indent=2, ensure_ascii=False)
        if user_context
        else "(none)"
    )
    outcomes_block = (
        json.dumps(expected_outcomes, indent=2, ensure_ascii=False)
        if expected_outcomes
        else "(none)"
    )

    return f"""You are simulating the USER in a conversation with an AI assistant (the agent under test).

PERSONA TYPE: {persona.type}

PERSONA DESCRIPTION:
{persona.description}

BEHAVIORAL INSTRUCTIONS (follow closely):
{persona.instructions}

BACKGROUND CONTEXT (only you know this; do not reveal you are a simulator):
{ctx_block}

YOUR GOAL / SUCCESS CRITERIA (what you are trying to achieve in the conversation):
{outcomes_block}

RULES:
- Stay in character at all times. Write only the next message the user would send.
- Be realistic: tone, length, and content should match the persona.
- Keep replies short and conversational by default (usually 1-2 sentences) unless your persona clearly calls for more.
- Do not dump all background context at once; reveal details only when it fits the persona and the flow of the conversation.
- Real customers are imperfect: they may omit details, push back, or answer only what was asked—avoid being unrealistically helpful or cooperative unless the persona says so.
- Respond naturally to what the assistant last said (the assistant's messages appear as user-role lines in your context due to role reversal in the API).
- Do not prefix with "User:" or similar. Output plain message text only.
- When the conversation has naturally reached a stopping point, you may send a brief closing message or thanks.
"""


class UserSimulator:
    """Generates the next user message (LLM persona or scripted replay)."""

    def __init__(
        self,
        persona: Persona,
        initial_message: str,
        user_context: dict[str, object] | None,
        expected_outcomes: dict[str, object] | None,
        config: UserSimulatorConfig,
    ) -> None:
        self._persona = persona
        self._initial_message = initial_message
        self._user_context = user_context
        self._expected_outcomes = expected_outcomes
        self._config = config
        self._scripted_index = 0
        self._system_prompt = _build_system_prompt(
            persona, user_context, expected_outcomes
        )

    def get_initial_message(self) -> str:
        return self._initial_message

    @property
    def is_exhausted(self) -> bool:
        if self._config.mode != SimulatorMode.SCRIPTED:
            return False
        return self._scripted_index >= len(self._config.scripted_messages)

    async def generate_message(
        self,
        conversation: list[LLMMessage],
    ) -> SimulatorResult:
        if self._config.mode == SimulatorMode.SCRIPTED:
            return self._next_scripted_message()
        return await self._generate_llm_message(conversation)

    def _next_scripted_message(self) -> SimulatorResult:
        if self.is_exhausted:
            msg = "No more scripted user messages"
            raise RuntimeError(msg)
        content = self._config.scripted_messages[self._scripted_index]
        self._scripted_index += 1
        return SimulatorResult(
            content=content, latency_ms=0, token_usage={}, cost_usd=None
        )

    async def _generate_llm_message(
        self,
        conversation: list[LLMMessage],
    ) -> SimulatorResult:
        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=self._system_prompt),
            *conversation,
        ]
        llm_config = LLMCallConfig(
            model=self._config.model,
            provider=self._config.provider,
            temperature=self._config.temperature,
        )
        response = await call_llm(messages, config=llm_config)
        return SimulatorResult(
            content=response.content.strip(),
            latency_ms=response.latency_ms,
            token_usage=dict(response.usage),
            cost_usd=response.response_cost_usd,
        )
