"""Tool dispatch: routes platform tool calls mock vs live according to RunConfig."""

import json
import logging
from collections import deque
from typing import Any, Literal

import httpx
from pydantic import ValidationError

from app.models.schemas import (
    ExpectedToolCall,
    HttpWebhookImplementation,
    MockResponse,
    PythonImplementation,
    ToolPlatformConfig,
)
from app.services.tool_executor import (
    SyntheticToolExecutor,
    ToolContext,
    ToolExecutor,
    execute_python_tool,
    execute_webhook_tool,
)

logger = logging.getLogger(__name__)


def extract_openai_function_tool_name(tool_def: dict[str, Any]) -> str | None:
    fn = tool_def.get("function")
    if isinstance(fn, dict):
        name = fn.get("name")
        if isinstance(name, str):
            return name
    return None


def validate_live_tool_snapshot(agent_tools: list[dict[str, Any]] | None) -> None:
    """Ensure every declared tool has ``platform_config`` with ``implementation``.

    Used when ``RunConfig.tool_mode`` is ``live`` for platform-mode agents.

    Raises:
        ValueError: If any tool is missing ``platform_config``, missing
            ``implementation``, or parsing fails.

    Does nothing when *agent_tools* is None or empty.
    """
    if not agent_tools:
        return

    missing_reasons: dict[str, str] = {}

    for tool_def in agent_tools:
        name = extract_openai_function_tool_name(tool_def)
        if not name:
            continue

        raw = tool_def.get("platform_config")
        if raw is None:
            missing_reasons[name] = "no platform_config"
            continue
        try:
            cfg = ToolPlatformConfig.model_validate(raw)
        except ValidationError:
            missing_reasons[name] = "invalid platform_config"
            continue
        if cfg.implementation is None:
            missing_reasons[name] = "no implementation on platform_config"

    if not missing_reasons:
        return

    parts = [f"'{nm}' ({reason})" for nm, reason in sorted(missing_reasons.items())]
    msg = (
        "Live tool mode requires each tool to have platform_config with implementation; "
        f"issues for: {', '.join(parts)}"
    )
    raise ValueError(msg)


def _partial_match(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """Check that every key in *expected* exists in *actual* with a matching value.

    String comparisons are case-insensitive and whitespace-stripped.
    """
    for key, exp_val in expected.items():
        if key not in actual:
            return False
        act_val = actual[key]
        if isinstance(exp_val, str) and isinstance(act_val, str):
            if exp_val.strip().lower() != act_val.strip().lower():
                return False
        elif exp_val != act_val:
            return False
    return True


class MockToolExecutor(ToolExecutor):
    """Returns canned mock responses from test case expected_tool_calls."""

    def __init__(self, expected_tool_calls: list[ExpectedToolCall]) -> None:
        self._queues: dict[str, deque[MockResponse]] = {}
        for etc in expected_tool_calls:
            if etc.mock_responses:
                self._queues.setdefault(etc.tool, deque()).extend(etc.mock_responses)

    async def execute(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: str,
    ) -> str:
        _ = tool_call_id
        queue = self._queues.get(tool_name)
        if not queue:
            return json.dumps(
                {"error": f"No mock response configured for tool '{tool_name}'"},
                ensure_ascii=False,
            )

        try:
            actual_args: dict[str, Any] = json.loads(arguments) if arguments else {}
        except (json.JSONDecodeError, TypeError):
            actual_args = {}

        for i, mock_resp in enumerate(queue):
            if mock_resp.expected_params is None or _partial_match(
                mock_resp.expected_params, actual_args
            ):
                del queue[i]
                return json.dumps(mock_resp.response, ensure_ascii=False)

        return json.dumps(
            {
                "error": (
                    f"No mock response matched arguments for tool '{tool_name}': "
                    f"{arguments}"
                )
            },
            ensure_ascii=False,
        )


class LiveToolExecutor(ToolExecutor):
    """Executes real tool implementations (Python code or HTTP webhooks)."""

    def __init__(
        self,
        tool_configs: dict[str, ToolPlatformConfig],
        test_case_context: dict[str, Any],
    ) -> None:
        self._tool_configs = tool_configs
        self._test_case_context = test_case_context

    async def execute(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: str,
    ) -> str:
        _ = tool_call_id
        config = self._tool_configs.get(tool_name)
        if config is None or config.implementation is None:
            return json.dumps(
                {"error": f"No live implementation configured for tool '{tool_name}'"},
                ensure_ascii=False,
            )

        try:
            parsed_args: dict[str, Any] = json.loads(arguments) if arguments else {}
        except (json.JSONDecodeError, TypeError):
            parsed_args = {}

        impl = config.implementation
        try:
            if isinstance(impl, PythonImplementation):
                result = await self._execute_python(impl, parsed_args)
            elif isinstance(impl, HttpWebhookImplementation):
                result = await self._execute_webhook(impl, parsed_args)
            else:
                result = {
                    "error": f"Unknown implementation type for tool '{tool_name}'"
                }
        except Exception as exc:
            logger.exception("Live tool '%s' raised unexpected error", tool_name)
            result = {"error": f"Tool execution failed: {type(exc).__name__}: {exc}"}

        return json.dumps(result, ensure_ascii=False)

    async def _execute_python(
        self,
        impl: PythonImplementation,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        context = ToolContext(
            http=httpx.AsyncClient(timeout=httpx.Timeout(impl.timeout_s)),
            config=impl.config,
            test_case_context=self._test_case_context,
        )
        try:
            return await execute_python_tool(
                code=impl.code,
                arguments=arguments,
                context=context,
                timeout_s=impl.timeout_s,
            )
        finally:
            await context.http.aclose()

    async def _execute_webhook(
        self,
        impl: HttpWebhookImplementation,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        return await execute_webhook_tool(
            url=impl.url,
            method=impl.method,
            headers=impl.headers,
            arguments=arguments,
            timeout_ms=impl.timeout_ms,
        )


def _parse_expected_tool_calls(
    raw: list[dict[str, Any]] | None,
) -> list[ExpectedToolCall]:
    parsed: list[ExpectedToolCall] = []
    for item in raw or []:
        if isinstance(item, dict):
            parsed.append(ExpectedToolCall.model_validate(item))
        elif isinstance(item, ExpectedToolCall):
            parsed.append(item)
    return parsed


def build_tool_executor(
    tools: list[dict[str, Any]] | None,
    expected_tool_calls: list[dict[str, Any]] | None,
    test_case_context: dict[str, Any],
    *,
    tool_mode: Literal["mock", "live", "synthetic"] = "mock",
) -> ToolExecutor:
    """Build the platform tool executor for one test case.

    Normally ``tool_mode`` mirrors ``RunConfig.tool_mode`` (``mock`` or
    ``live``). The value ``synthetic`` is reserved for internal/CLI use: it
    always returns :class:`SyntheticToolExecutor`, matching legacy behavior when
    tools had no ``platform_config``.
    """
    if tool_mode == "synthetic":
        return SyntheticToolExecutor()

    if not tools:
        return SyntheticToolExecutor()

    parsed_etc = _parse_expected_tool_calls(expected_tool_calls)

    if tool_mode == "mock":
        return MockToolExecutor(parsed_etc)

    live_configs: dict[str, ToolPlatformConfig] = {}
    for tool_def in tools:
        name = extract_openai_function_tool_name(tool_def)
        if not name:
            continue
        raw_pc = tool_def.get("platform_config")
        if raw_pc is None:
            continue
        cfg = ToolPlatformConfig.model_validate(raw_pc)
        if cfg.implementation is not None:
            live_configs[name] = cfg

    return LiveToolExecutor(live_configs, test_case_context)
