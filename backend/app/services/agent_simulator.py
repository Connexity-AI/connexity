"""Platform-side agent turn simulation via :func:`call_llm` and optional tools."""

import logging
from typing import Any

from pydantic import BaseModel

from app.models.agent_contract import ChatMessage
from app.models.enums import TurnRole
from app.models.schemas import AgentSimulatorConfig, ToolCall, ToolCallFunction
from app.services.agent_tool_definitions import snapshot_marks_tool_terminating
from app.services.cost_tracker import sum_usage_dicts
from app.services.llm import LLMCallConfig, LLMMessage, call_llm
from app.services.tool_executor import SyntheticToolExecutor, ToolExecutor

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 16


class AgentSimulatorResult(BaseModel):
    """One simulated agent turn: messages, timing, usage, and cost."""

    messages: list[ChatMessage]
    latency_ms: int
    token_usage: dict[str, int]
    cost_usd: float | None
    model: str | None
    provider: str | None


def _parse_resolved_model(resolved: str) -> tuple[str, str | None]:
    if "/" in resolved:
        prov, rest = resolved.split("/", 1)
        return rest, prov
    return resolved, None


def _tool_calls_dicts_to_models(raw: list[dict[str, Any]]) -> list[ToolCall]:
    out: list[ToolCall] = []
    for d in raw:
        tc_id = str(d.get("id", ""))
        fn = d.get("function")
        if isinstance(fn, dict):
            name = str(fn.get("name", ""))
            arguments = str(fn.get("arguments", "{}"))
        else:
            name = ""
            arguments = "{}"
        out.append(
            ToolCall(
                id=tc_id,
                type="function",
                function=ToolCallFunction(name=name, arguments=arguments),
            )
        )
    return out


_PLATFORM_ONLY_KEYS = frozenset({"platform_config"})


def _strip_platform_keys(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove platform-internal keys (e.g. ``platform_config``) before sending to LLM."""
    return [
        {k: v for k, v in tool.items() if k not in _PLATFORM_ONLY_KEYS}
        for tool in tools
    ]


_TURN_TO_LLM_ROLE: dict[TurnRole, str] = {
    TurnRole.SYSTEM: "system",
    TurnRole.USER: "user",
    TurnRole.ASSISTANT: "assistant",
    TurnRole.TOOL: "tool",
}


def _chat_messages_to_llm_messages(messages: list[ChatMessage]) -> list[LLMMessage]:
    out: list[LLMMessage] = []
    for m in messages:
        role_str = _TURN_TO_LLM_ROLE[m.role]
        tc_dicts: list[dict[str, Any]] | None = None
        if m.tool_calls:
            tc_dicts = [tc.model_dump(mode="json") for tc in m.tool_calls]
        out.append(
            LLMMessage(
                role=role_str,  # type: ignore[arg-type]
                content=m.content,
                tool_calls=tc_dicts,
                tool_call_id=m.tool_call_id,
                name=m.name,
            )
        )
    return out


class AgentSimulator:
    """Simulates an agent turn via the platform LLM (mirrors :class:`UserSimulator`)."""

    def __init__(
        self,
        system_prompt: str,
        tools: list[dict[str, Any]] | None,
        agent_model: str,
        agent_provider: str | None,
        config: AgentSimulatorConfig | None = None,
        *,
        tool_executor: ToolExecutor | None = None,
    ) -> None:
        self._system_prompt = system_prompt
        self._raw_tools = tools
        self._tools = _strip_platform_keys(tools) if tools else tools
        self._tool_executor = tool_executor or SyntheticToolExecutor()
        cfg = config
        self._model = cfg.model if cfg and cfg.model else agent_model
        self._provider = cfg.provider if cfg and cfg.provider else agent_provider
        self._temperature = cfg.temperature if cfg else None
        self._max_tokens = cfg.max_tokens if cfg else None

    async def generate_response(
        self,
        messages: list[ChatMessage],
    ) -> AgentSimulatorResult:
        """Produce one agent turn (may include tool calls and follow-up assistant)."""
        llm_messages: list[LLMMessage] = [
            LLMMessage(role="system", content=self._system_prompt),
            *_chat_messages_to_llm_messages(messages),
        ]
        llm_cfg = LLMCallConfig(
            model=self._model,
            provider=self._provider,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            tools=self._tools,
        )

        output_messages: list[ChatMessage] = []
        usage_parts: list[dict[str, int]] = []
        total_cost = 0.0
        total_latency = 0
        last_model: str | None = None
        last_provider: str | None = None

        for _ in range(_MAX_TOOL_ROUNDS):
            try:
                response = await call_llm(llm_messages, config=llm_cfg)
            except Exception as exc:
                raise RuntimeError(
                    f"Agent simulator LLM call failed (model={self._model}): {exc}"
                ) from exc
            total_latency += response.latency_ms or 0
            usage_parts.append(dict(response.usage))
            if response.response_cost_usd is not None:
                total_cost += float(response.response_cost_usd)
            last_model, last_provider = _parse_resolved_model(response.model)

            if not response.tool_calls:
                output_messages.append(
                    ChatMessage(
                        role=TurnRole.ASSISTANT,
                        content=response.content or None,
                        tool_calls=None,
                        tool_call_id=None,
                        name=None,
                    )
                )
                break

            tool_models = _tool_calls_dicts_to_models(response.tool_calls)
            output_messages.append(
                ChatMessage(
                    role=TurnRole.ASSISTANT,
                    content=response.content or None,
                    tool_calls=tool_models,
                    tool_call_id=None,
                    name=None,
                )
            )

            if any(
                snapshot_marks_tool_terminating(tc.function.name, self._raw_tools)
                for tc in tool_models
            ):
                break

            llm_messages.append(
                LLMMessage(
                    role="assistant",
                    content=response.content or None,
                    tool_calls=response.tool_calls,
                )
            )

            for tc in tool_models:
                result_str = await self._tool_executor.execute(
                    tc.function.name,
                    tc.id,
                    tc.function.arguments,
                )
                output_messages.append(
                    ChatMessage(
                        role=TurnRole.TOOL,
                        content=result_str,
                        tool_calls=None,
                        tool_call_id=tc.id,
                        name=tc.function.name,
                    )
                )
                llm_messages.append(
                    LLMMessage(
                        role="tool",
                        content=result_str,
                        tool_call_id=tc.id,
                        name=tc.function.name,
                    )
                )
        else:
            logger.warning(
                "Agent simulator stopped after %d tool rounds without a final reply",
                _MAX_TOOL_ROUNDS,
            )
            if output_messages and output_messages[-1].role != TurnRole.ASSISTANT:
                output_messages.append(
                    ChatMessage(
                        role=TurnRole.ASSISTANT,
                        content=(
                            "[platform: agent simulator tool round limit exceeded]"
                        ),
                        tool_calls=None,
                        tool_call_id=None,
                        name=None,
                    )
                )

        merged_usage = sum_usage_dicts(*usage_parts)
        int_usage: dict[str, int] = {
            k: int(v)
            for k, v in merged_usage.items()
            if k != "estimated" and not isinstance(v, bool)
        }

        return AgentSimulatorResult(
            messages=output_messages,
            latency_ms=total_latency,
            token_usage=int_usage,
            cost_usd=total_cost if total_cost > 0 else None,
            model=last_model,
            provider=last_provider,
        )
