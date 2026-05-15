"""Custom endpoint text runtime.

Runs the shared in-process **user simulator** against an **HTTP agent endpoint**
(OpenAI-compatible contract). Agent inference never goes through
:class:`~app.services.agent_simulator.AgentSimulator` — that path is
:class:`ConnexityRuntime`.

See :mod:`app.models.agent_contract` for ``AgentRequest`` / ``AgentResponse``.
"""

import logging
import time
from typing import ClassVar

import httpx
from pydantic import ValidationError
from sqlmodel import Session

from app.core.config import settings
from app.models.agent import Agent
from app.models.agent_contract import (
    AgentRequest,
    AgentRequestMetadata,
    AgentResponse,
    ChatMessage,
    TokenUsage,
)
from app.models.enums import AgentMode, Platform, RunMode, TextRuntimeKind, TurnRole
from app.models.schemas import CustomEndpointRuntimeConfig, RuntimeConfig
from app.services.cost_tracker import estimate_agent_cost, estimate_agent_tokens
from app.services.eval_runtimes.base import RuntimeRunArgs, RuntimeTestResult
from app.services.eval_runtimes.text.base import (
    TextAgentTurnConfig,
    TextAgentTurnContext,
    TextRuntimeBase,
)

logger = logging.getLogger(__name__)

_TEST_TIMEOUT_SECONDS = 10.0


class AgentEndpointHttpError(Exception):
    """Agent endpoint request failed (network, timeout, or HTTP error)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class CustomEndpointRuntime(TextRuntimeBase):
    MODE: ClassVar[RunMode] = RunMode.TEXT
    KIND: ClassVar[TextRuntimeKind] = TextRuntimeKind.CUSTOM_ENDPOINT
    LABEL: ClassVar[str] = "Your Agent"
    DESCRIPTION: ClassVar[str] = "Run evaluations against your own agent"

    def supported_for_platform(self, platform: Platform | None) -> bool:
        # Retell agents use the Retell runtime or Connexity; HTTP custom URL is not offered.
        return platform != Platform.RETELL

    def validate_config(
        self,
        runtime_config: RuntimeConfig,
        agent: Agent,
        session: Session,
    ) -> None:
        if not isinstance(runtime_config, CustomEndpointRuntimeConfig):
            msg = "custom_endpoint runtime requires a CustomEndpointRuntimeConfig"
            raise ValueError(msg)
        url = runtime_config.url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            msg = "url must start with http:// or https://"
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

        assert isinstance(runtime_config, CustomEndpointRuntimeConfig)

        probe = AgentRequest(messages=[ChatMessage(role=TurnRole.USER, content="ping")])
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    runtime_config.url,
                    json=probe.model_dump(mode="json", exclude_none=True),
                    timeout=_TEST_TIMEOUT_SECONDS,
                )
        except httpx.HTTPError as exc:
            return RuntimeTestResult(ok=False, message=f"Network error: {exc}")

        if response.status_code >= 400:
            return RuntimeTestResult(
                ok=False,
                message=f"HTTP {response.status_code} from URL",
            )

        try:
            AgentResponse.model_validate(response.json())
        except ValueError as exc:
            return RuntimeTestResult(
                ok=False,
                message=f"Response does not match AgentResponse contract: {exc}",
            )

        return RuntimeTestResult(
            ok=True, message="URL responded with a valid AgentResponse."
        )

    def build_text_agent_config(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TextAgentTurnConfig:
        if not isinstance(runtime_config, CustomEndpointRuntimeConfig):
            msg = "custom_endpoint runtime requires a CustomEndpointRuntimeConfig"
            raise ValueError(msg)

        agent = args.agent_snapshot
        return TextAgentTurnConfig(
            endpoint_url=runtime_config.url,
            agent_mode=AgentMode.ENDPOINT,
            model=agent.model,
            provider=agent.provider,
            system_prompt=agent.system_prompt,
            tools=agent.tools,
        )

    async def do_agent_turn(self, context: TextAgentTurnContext) -> bool:
        endpoint_url = context.agent_config.endpoint_url
        if not endpoint_url:
            logger.error("Custom endpoint runtime missing configured URL")
            context.transcript.append(
                self.build_conversation_turn(
                    index=len(context.transcript),
                    role=TurnRole.ASSISTANT,
                    content="[agent_error] missing agent endpoint URL",
                    latency_ms=None,
                )
            )
            return False

        agent_messages = self.transcript_to_agent_messages(context.transcript)
        metadata = AgentRequestMetadata(
            test_case_id=str(context.test_case.id),
            turn_index=len(context.transcript),
        )
        try:
            response, round_latency_ms = await self._post_agent_request(
                endpoint_url,
                agent_messages,
                timeout_ms=context.remaining_ms,
                metadata=metadata,
            )
        except AgentEndpointHttpError as exc:
            logger.warning(
                "Agent HTTP request failed for test_case %s: %s",
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

        reported = self._usage_dict_from_token_usage(response.usage)
        if reported is not None:
            context.accumulator.add_agent_usage(reported)
        else:
            reported = estimate_agent_tokens(
                prompt_messages=agent_messages,
                response_messages=response.messages,
                agent_system_prompt=context.agent_config.system_prompt,
                agent_tools=context.agent_config.tools,
                model=response.model,
                fallback_model=settings.default_llm_id,
            )
            context.accumulator.add_agent_usage(reported)

        if reported.get("prompt_tokens") or reported.get("completion_tokens"):
            context.accumulator.add_agent_cost(
                estimate_agent_cost(
                    model=response.model,
                    provider=response.provider,
                    usage=reported,
                )
            )

        self.append_wire_messages_to_transcript(
            context.transcript, response, round_latency_ms
        )
        return True

    async def _post_agent_request(
        self,
        endpoint_url: str,
        messages: list[ChatMessage],
        timeout_ms: int,
        *,
        metadata: AgentRequestMetadata | None,
        client: httpx.AsyncClient | None = None,
    ) -> tuple[AgentResponse, int]:
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
            except httpx.TimeoutException as exc:
                msg = f"Agent request timed out after {timeout_ms}ms"
                raise AgentEndpointHttpError(msg) from exc
            except httpx.RequestError as exc:
                msg = f"Agent request failed: {exc}"
                raise AgentEndpointHttpError(msg) from exc
        finally:
            if owns_client:
                await client.aclose()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if resp.is_error:
            msg = f"Agent HTTP {resp.status_code}: {resp.text[:500]}"
            raise AgentEndpointHttpError(msg, status_code=resp.status_code)
        try:
            data = resp.json()
        except ValueError as exc:
            msg = "Agent response is not valid JSON"
            raise AgentEndpointHttpError(msg) from exc
        try:
            parsed = AgentResponse.model_validate(data)
        except ValidationError as exc:
            msg = f"Agent response JSON does not match contract: {exc}"
            raise AgentEndpointHttpError(msg) from exc
        return parsed, elapsed_ms

    def _usage_dict_from_token_usage(
        self, usage: TokenUsage | None
    ) -> dict[str, int] | None:
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
