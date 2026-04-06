"""Tests for :mod:`app.services.tool_executor` — Python sandbox and HTTP webhook."""

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.tool_executor import (
    ToolContext,
    ToolExecutionError,
    execute_python_tool,
    execute_webhook_tool,
)


def _make_context(**overrides: object) -> ToolContext:
    return ToolContext(
        http=AsyncMock(spec=httpx.AsyncClient),
        config=overrides.get("config", {}),  # type: ignore[arg-type]
        test_case_context=overrides.get("test_case_context", {}),  # type: ignore[arg-type]
    )


# ── execute_python_tool ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_python_tool_happy_path() -> None:
    code = (
        "async def execute(args, context):\n" "    return {'doubled': args['x'] * 2}\n"
    )
    result = await execute_python_tool(code, {"x": 5}, _make_context())
    assert result == {"doubled": 10}


@pytest.mark.asyncio
async def test_python_tool_syntax_error() -> None:
    result = await execute_python_tool("def execute(:\n", {}, _make_context())
    assert "error" in result
    assert "Syntax error" in result["error"]


@pytest.mark.asyncio
async def test_python_tool_missing_execute_function() -> None:
    code = "async def run(args, context):\n    return {}\n"
    result = await execute_python_tool(code, {}, _make_context())
    assert "error" in result
    assert "must define" in result["error"]


@pytest.mark.asyncio
async def test_python_tool_returns_non_dict() -> None:
    code = "async def execute(args, context):\n    return 'not a dict'\n"
    result = await execute_python_tool(code, {}, _make_context())
    assert "error" in result
    assert "must return dict" in result["error"]
    assert "str" in result["error"]


@pytest.mark.asyncio
async def test_python_tool_timeout() -> None:
    code = (
        "async def execute(args, context):\n"
        "    await asyncio.sleep(999)\n"
        "    return {}\n"
    )
    result = await execute_python_tool(code, {}, _make_context(), timeout_s=0.05)
    assert "error" in result
    assert "timed out" in result["error"]


@pytest.mark.asyncio
async def test_python_tool_namespace_blocks_os() -> None:
    code = (
        "import os\n"
        "async def execute(args, context):\n"
        "    return {'cwd': os.getcwd()}\n"
    )
    result = await execute_python_tool(code, {}, _make_context())
    assert "error" in result


@pytest.mark.asyncio
async def test_python_tool_namespace_blocks_open() -> None:
    code = (
        "async def execute(args, context):\n"
        "    f = open('/etc/passwd')\n"
        "    return {'data': f.read()}\n"
    )
    result = await execute_python_tool(code, {}, _make_context())
    assert "error" in result


@pytest.mark.asyncio
async def test_python_tool_uses_context_config() -> None:
    code = (
        "async def execute(args, context):\n"
        "    return {'url': context.config['base_url']}\n"
    )
    ctx = _make_context(config={"base_url": "https://example.com"})
    result = await execute_python_tool(code, {}, ctx)
    assert result == {"url": "https://example.com"}


@pytest.mark.asyncio
async def test_python_tool_uses_test_case_context() -> None:
    code = (
        "async def execute(args, context):\n"
        "    return {'customer': context.test_case_context['customer_name']}\n"
    )
    ctx = _make_context(test_case_context={"customer_name": "Alice"})
    result = await execute_python_tool(code, {}, ctx)
    assert result == {"customer": "Alice"}


@pytest.mark.asyncio
async def test_python_tool_runtime_error() -> None:
    code = "async def execute(args, context):\n" "    return 1 / 0\n"
    result = await execute_python_tool(code, {}, _make_context())
    assert "error" in result
    assert "ZeroDivisionError" in result["error"]


# ── ToolContext.secret ────────────────────────────────────────────


def test_tool_context_secret_present() -> None:
    ctx = _make_context()
    with patch.dict(os.environ, {"MY_API_KEY": "sk-123"}):
        assert ctx.secret("MY_API_KEY") == "sk-123"


def test_tool_context_secret_missing() -> None:
    ctx = _make_context()
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ToolExecutionError, match="MY_MISSING_KEY"):
            ctx.secret("MY_MISSING_KEY")


@pytest.mark.asyncio
async def test_python_tool_secret_in_code() -> None:
    code = (
        "async def execute(args, context):\n"
        "    key = context.secret('TEST_KEY')\n"
        "    return {'key': key}\n"
    )
    ctx = _make_context()
    with patch.dict(os.environ, {"TEST_KEY": "secret-value"}):
        result = await execute_python_tool(code, {}, ctx)
    assert result == {"key": "secret-value"}


@pytest.mark.asyncio
async def test_python_tool_secret_missing_returns_error() -> None:
    code = (
        "async def execute(args, context):\n"
        "    return {'key': context.secret('NOPE')}\n"
    )
    with patch.dict(os.environ, {}, clear=True):
        result = await execute_python_tool(code, {}, _make_context())
    assert "error" in result
    assert "NOPE" in result["error"]


# ── execute_webhook_tool ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_happy_path() -> None:
    mock_response = httpx.Response(
        200,
        json={"order_id": "ORD-1", "status": "shipped"},
        request=httpx.Request("POST", "https://api.example.com/orders"),
    )
    with patch("app.services.tool_executor.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.request.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = instance

        result = await execute_webhook_tool(
            url="https://api.example.com/orders",
            method="POST",
            headers={"Content-Type": "application/json"},
            arguments={"order_id": "ORD-1"},
            timeout_ms=5000,
        )

    assert result == {"order_id": "ORD-1", "status": "shipped"}
    instance.request.assert_awaited_once()
    call_kwargs = instance.request.call_args.kwargs
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["json"] == {"order_id": "ORD-1"}


@pytest.mark.asyncio
async def test_webhook_env_interpolation() -> None:
    mock_response = httpx.Response(
        200,
        json={"ok": True},
        request=httpx.Request("POST", "https://api.example.com"),
    )
    with (
        patch.dict(
            os.environ, {"API_HOST": "api.example.com", "API_KEY": "bearer-123"}
        ),
        patch("app.services.tool_executor.httpx.AsyncClient") as mock_client_cls,
    ):
        instance = AsyncMock()
        instance.request.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = instance

        result = await execute_webhook_tool(
            url="https://${API_HOST}/endpoint",
            method="POST",
            headers={"Authorization": "Bearer ${API_KEY}"},
            arguments={},
        )

    assert result == {"ok": True}
    call_kwargs = instance.request.call_args.kwargs
    assert call_kwargs["url"] == "https://api.example.com/endpoint"
    assert call_kwargs["headers"]["Authorization"] == "Bearer bearer-123"


@pytest.mark.asyncio
async def test_webhook_missing_env_var() -> None:
    with patch.dict(os.environ, {}, clear=True):
        result = await execute_webhook_tool(
            url="https://${MISSING_HOST}/endpoint",
            method="POST",
            headers=None,
            arguments={},
        )
    assert "error" in result
    assert "MISSING_HOST" in result["error"]


@pytest.mark.asyncio
async def test_webhook_http_error() -> None:
    mock_response = httpx.Response(
        500,
        text="Internal Server Error",
        request=httpx.Request("POST", "https://api.example.com"),
    )
    with patch("app.services.tool_executor.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.request.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = instance

        result = await execute_webhook_tool(
            url="https://api.example.com",
            method="POST",
            headers=None,
            arguments={},
        )

    assert "error" in result
    assert "500" in result["error"]


@pytest.mark.asyncio
async def test_webhook_non_json_response() -> None:
    mock_response = httpx.Response(
        200,
        text="plain text result",
        request=httpx.Request("GET", "https://api.example.com"),
    )
    with patch("app.services.tool_executor.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.request.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = instance

        result = await execute_webhook_tool(
            url="https://api.example.com",
            method="GET",
            headers=None,
            arguments={},
        )

    assert result == {"result": "plain text result"}
