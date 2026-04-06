"""Tool dispatch: routes tool calls to mock, live, or synthetic executors."""

import json
import logging
from collections import deque
from typing import Any

import httpx

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


class CompositeToolExecutor(ToolExecutor):
    """Routes each tool call to the correct executor based on platform_config.mode."""

    def __init__(
        self,
        tool_modes: dict[str, str],
        mock: MockToolExecutor,
        live: LiveToolExecutor,
    ) -> None:
        self._tool_modes = tool_modes
        self._mock = mock
        self._live = live
        self._synthetic = SyntheticToolExecutor()

    async def execute(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: str,
    ) -> str:
        mode = self._tool_modes.get(tool_name)
        if mode == "mock":
            return await self._mock.execute(tool_name, tool_call_id, arguments)
        if mode == "live":
            return await self._live.execute(tool_name, tool_call_id, arguments)
        return await self._synthetic.execute(tool_name, tool_call_id, arguments)


def _extract_tool_name(tool_def: dict[str, Any]) -> str | None:
    fn = tool_def.get("function")
    if isinstance(fn, dict):
        name = fn.get("name")
        if isinstance(name, str):
            return name
    return None


def build_tool_executor(
    tools: list[dict[str, Any]] | None,
    expected_tool_calls: list[dict[str, Any]] | None,
    test_case_context: dict[str, Any],
) -> ToolExecutor:
    """Build the appropriate ToolExecutor from agent tools and test case data.

    Returns :class:`CompositeToolExecutor` when any tool has ``platform_config``,
    otherwise :class:`SyntheticToolExecutor` for CS-54 backward compatibility.
    """
    if not tools:
        return SyntheticToolExecutor()

    tool_modes: dict[str, str] = {}
    live_configs: dict[str, ToolPlatformConfig] = {}
    has_platform_config = False

    for tool_def in tools:
        name = _extract_tool_name(tool_def)
        if not name:
            continue

        raw_config = tool_def.get("platform_config")
        if raw_config is None:
            continue

        has_platform_config = True
        parsed = ToolPlatformConfig.model_validate(raw_config)
        tool_modes[name] = parsed.mode

        if parsed.mode == "live":
            live_configs[name] = parsed

    if not has_platform_config:
        return SyntheticToolExecutor()

    parsed_etc: list[ExpectedToolCall] = []
    for raw in expected_tool_calls or []:
        if isinstance(raw, dict):
            parsed_etc.append(ExpectedToolCall.model_validate(raw))
        elif isinstance(raw, ExpectedToolCall):
            parsed_etc.append(raw)

    mock_executor = MockToolExecutor(parsed_etc)
    live_executor = LiveToolExecutor(live_configs, test_case_context)

    return CompositeToolExecutor(
        tool_modes=tool_modes,
        mock=mock_executor,
        live=live_executor,
    )
