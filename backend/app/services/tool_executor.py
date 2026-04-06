"""Tool execution layer: base contract, context, Python sandbox, and HTTP webhook."""

import asyncio
import datetime
import json
import logging
import math
import os
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_ENV_VAR_RE = re.compile(r"\$\{(\w+)\}")


class ToolExecutor(ABC):
    """Base class for all tool executors (synthetic, mock, live, composite)."""

    @abstractmethod
    async def execute(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: str,
    ) -> str:
        """Return tool result as a string (typically JSON)."""


class SyntheticToolExecutor(ToolExecutor):
    """Placeholder tool results when no mock or live executor is configured."""

    async def execute(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: str,
    ) -> str:
        _ = tool_name, tool_call_id, arguments
        return json.dumps(
            {
                "status": "simulated",
                "note": "Tool not executed by platform agent simulator",
            },
            ensure_ascii=False,
        )


class ToolExecutionError(Exception):
    """Raised inside tool code when a required resource is unavailable."""


@dataclass
class ToolContext:
    """Controlled runtime environment passed to user-written Python tools."""

    http: httpx.AsyncClient
    config: dict[str, Any] = field(default_factory=dict)
    test_case_context: dict[str, Any] = field(default_factory=dict)

    def secret(self, name: str) -> str:
        """Resolve a server-side environment variable by name."""
        value = os.environ.get(name)
        if value is None:
            raise ToolExecutionError(
                f"Secret '{name}' is not set in the server environment"
            )
        return value


_BLOCKED_BUILTINS = frozenset(
    {
        "__import__",
        "open",
        "exec",
        "eval",
        "compile",
        "breakpoint",
        "exit",
        "quit",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "input",
        "memoryview",
    }
)

_SAFE_BUILTINS: dict[str, Any] = {
    k: v
    for k, v in __builtins__.items()  # type: ignore[union-attr]
    if k not in _BLOCKED_BUILTINS
}

TOOL_NAMESPACE: dict[str, Any] = {
    "__builtins__": _SAFE_BUILTINS,
    "asyncio": asyncio,
    "httpx": httpx,
    "json": json,
    "re": re,
    "math": math,
    "datetime": datetime,
    "uuid": uuid,
    "Any": Any,
    "dict": dict,
    "list": list,
    "ToolContext": ToolContext,
    "ToolExecutionError": ToolExecutionError,
}


async def execute_python_tool(
    code: str,
    arguments: dict[str, Any],
    context: ToolContext,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Execute user-written Python tool code in a restricted namespace.

    The code must define ``async def execute(args, context) -> dict``.
    All errors are caught and returned as ``{"error": ...}`` dicts.
    """
    try:
        compiled = compile(code, "<tool>", "exec")
    except SyntaxError as exc:
        return {"error": f"Syntax error in tool code: {exc}"}

    namespace: dict[str, Any] = {**TOOL_NAMESPACE}
    try:
        exec(compiled, namespace)  # noqa: S102
    except Exception as exc:
        return {"error": f"Error loading tool code: {exc}"}

    fn = namespace.get("execute")
    if fn is None or not callable(fn):
        return {
            "error": "Tool code must define: async def execute(args, context) -> dict"
        }

    try:
        coro = fn(arguments, context)
        result = await asyncio.wait_for(coro, timeout=timeout_s)  # type: ignore[arg-type]
    except TimeoutError:
        return {"error": f"Tool execution timed out after {timeout_s}s"}
    except ToolExecutionError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": f"Tool execution failed: {type(exc).__name__}: {exc}"}

    if not isinstance(result, dict):
        return {"error": f"Tool must return dict, got {type(result).__name__}"}
    return result


def _interpolate_env_vars(value: str) -> str:
    """Replace ``${VAR}`` placeholders with environment variable values."""

    def _replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        env_val = os.environ.get(var_name)
        if env_val is None:
            raise ToolExecutionError(
                f"Environment variable '{var_name}' required by webhook is not set"
            )
        return env_val

    return _ENV_VAR_RE.sub(_replace, value)


async def execute_webhook_tool(
    url: str,
    method: str,
    headers: dict[str, str] | None,
    arguments: dict[str, Any],
    timeout_ms: int = 10000,
) -> dict[str, Any]:
    """Execute an HTTP webhook tool call.

    Tool arguments are sent as the JSON body. ``${VAR}`` placeholders in the
    URL and header values are interpolated from server environment variables.
    """
    try:
        resolved_url = _interpolate_env_vars(url)
        resolved_headers: dict[str, str] | None = None
        if headers:
            resolved_headers = {k: _interpolate_env_vars(v) for k, v in headers.items()}
    except ToolExecutionError as exc:
        return {"error": str(exc)}

    timeout = httpx.Timeout(timeout_ms / 1000.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method.upper(),
                url=resolved_url,
                json=arguments,
                headers=resolved_headers,
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        return {"error": f"Webhook request timed out after {timeout_ms}ms"}
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        return {"error": f"Webhook returned HTTP {exc.response.status_code}: {body}"}
    except httpx.HTTPError as exc:
        return {"error": f"Webhook request failed: {exc}"}

    try:
        return response.json()  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return {"result": response.text}
