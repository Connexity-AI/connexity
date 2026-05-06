"""Tests for :mod:`app.services.tool_dispatch` — mock vs live run-scoped routing."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import (
    ExpectedToolCall,
    HttpWebhookImplementation,
    MockResponse,
    PythonImplementation,
    ToolPlatformConfig,
)
from app.services.agent_tool_definitions import canonical_end_call_tool_dict
from app.services.tool_dispatch import (
    LiveToolExecutor,
    MockToolExecutor,
    build_tool_executor,
    validate_live_tool_snapshot,
)
from app.services.tool_executor import SyntheticToolExecutor

# ── MockToolExecutor ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mock_sequential_consumption() -> None:
    etc = [
        ExpectedToolCall(
            tool="lookup",
            mock_responses=[
                MockResponse(
                    expected_params=None,
                    response={"result": "first"},
                ),
                MockResponse(
                    expected_params=None,
                    response={"result": "second"},
                ),
            ],
        )
    ]
    executor = MockToolExecutor(etc)

    r1 = json.loads(await executor.execute("lookup", "c1", "{}"))
    assert r1 == {"result": "first"}

    r2 = json.loads(await executor.execute("lookup", "c2", "{}"))
    assert r2 == {"result": "second"}

    r3 = json.loads(await executor.execute("lookup", "c3", "{}"))
    assert "error" in r3


@pytest.mark.asyncio
async def test_mock_partial_param_matching() -> None:
    etc = [
        ExpectedToolCall(
            tool="search",
            mock_responses=[
                MockResponse(
                    expected_params={"query": "weather"},
                    response={"temp": 72},
                ),
                MockResponse(
                    expected_params={"query": "news"},
                    response={"headline": "Breaking"},
                ),
            ],
        )
    ]
    executor = MockToolExecutor(etc)

    r1 = json.loads(
        await executor.execute(
            "search", "c1", json.dumps({"query": "weather", "lang": "en"})
        )
    )
    assert r1 == {"temp": 72}

    r2 = json.loads(
        await executor.execute("search", "c2", json.dumps({"query": "news"}))
    )
    assert r2 == {"headline": "Breaking"}


@pytest.mark.asyncio
async def test_mock_case_insensitive_string_match() -> None:
    etc = [
        ExpectedToolCall(
            tool="greet",
            mock_responses=[
                MockResponse(
                    expected_params={"name": "Alice"},
                    response={"greeting": "Hello Alice"},
                ),
            ],
        )
    ]
    executor = MockToolExecutor(etc)

    r = json.loads(
        await executor.execute("greet", "c1", json.dumps({"name": "  alice  "}))
    )
    assert r == {"greeting": "Hello Alice"}


@pytest.mark.asyncio
async def test_mock_no_match_returns_error() -> None:
    etc = [
        ExpectedToolCall(
            tool="lookup",
            mock_responses=[
                MockResponse(
                    expected_params={"id": "X"},
                    response={"found": True},
                ),
            ],
        )
    ]
    executor = MockToolExecutor(etc)

    r = json.loads(await executor.execute("lookup", "c1", json.dumps({"id": "Y"})))
    assert "error" in r
    assert "No mock response matched" in r["error"]


@pytest.mark.asyncio
async def test_mock_unknown_tool() -> None:
    executor = MockToolExecutor([])
    r = json.loads(await executor.execute("unknown_tool", "c1", "{}"))
    assert "error" in r
    assert "No mock response configured" in r["error"]


# ── LiveToolExecutor ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_live_routes_python() -> None:
    configs = {
        "compute": ToolPlatformConfig(
            implementation=PythonImplementation(
                code="async def execute(args, ctx): return {'sum': args['a'] + args['b']}",
            ),
        ),
    }
    executor = LiveToolExecutor(configs, test_case_context={})

    with patch(
        "app.services.tool_dispatch.execute_python_tool",
        new_callable=AsyncMock,
        return_value={"sum": 3},
    ) as mock_py:
        result = json.loads(
            await executor.execute("compute", "c1", json.dumps({"a": 1, "b": 2}))
        )

    assert result == {"sum": 3}
    mock_py.assert_awaited_once()
    call_kwargs = mock_py.call_args.kwargs
    assert call_kwargs["arguments"] == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_live_routes_webhook() -> None:
    configs = {
        "notify": ToolPlatformConfig(
            implementation=HttpWebhookImplementation(
                url="https://hook.example.com",
                method="POST",
            ),
        ),
    }
    executor = LiveToolExecutor(configs, test_case_context={})

    with patch(
        "app.services.tool_dispatch.execute_webhook_tool",
        new_callable=AsyncMock,
        return_value={"sent": True},
    ) as mock_wh:
        result = json.loads(
            await executor.execute("notify", "c1", json.dumps({"msg": "hi"}))
        )

    assert result == {"sent": True}
    mock_wh.assert_awaited_once()


@pytest.mark.asyncio
async def test_live_unknown_tool_returns_error() -> None:
    executor = LiveToolExecutor({}, test_case_context={})
    result = json.loads(await executor.execute("missing", "c1", "{}"))
    assert "error" in result
    assert "No live implementation" in result["error"]


# ── build_tool_executor ───────────────────────────────────────────


def test_build_no_tools_returns_synthetic() -> None:
    executor = build_tool_executor(
        tools=None,
        expected_tool_calls=None,
        test_case_context={},
        tool_mode="mock",
    )
    assert isinstance(executor, SyntheticToolExecutor)


def test_build_mock_mode_returns_mock_even_without_platform_config() -> None:
    tools = [
        {
            "type": "function",
            "function": {"name": "search", "parameters": {}},
        }
    ]
    executor = build_tool_executor(
        tools=tools,
        expected_tool_calls=None,
        test_case_context={},
        tool_mode="mock",
    )
    assert isinstance(executor, MockToolExecutor)


def test_build_live_mode_returns_live_when_implementations_present() -> None:
    tools = [
        {
            "type": "function",
            "function": {"name": "compute"},
            "platform_config": {
                "implementation": {
                    "type": "python",
                    "code": "async def execute(a, c): return {}",
                },
            },
        },
    ]
    executor = build_tool_executor(
        tools=tools,
        expected_tool_calls=None,
        test_case_context={"key": "val"},
        tool_mode="live",
    )
    assert isinstance(executor, LiveToolExecutor)


def test_build_mock_mode_uses_expected_tool_calls() -> None:
    tools = [
        {
            "type": "function",
            "function": {"name": "lookup"},
            "platform_config": {
                "implementation": {
                    "type": "python",
                    "code": "async def execute(a, c): return {}",
                },
            },
        },
    ]
    expected = [
        {
            "tool": "lookup",
            "mock_responses": [
                {"expected_params": None, "response": {"found": True}},
            ],
        }
    ]
    executor = build_tool_executor(
        tools=tools,
        expected_tool_calls=expected,
        test_case_context={"key": "val"},
        tool_mode="mock",
    )
    assert isinstance(executor, MockToolExecutor)


def test_build_synthetic_mode_returns_placeholder_executor() -> None:
    tools = [
        {"type": "function", "function": {"name": "x"}},
    ]
    executor = build_tool_executor(
        tools=tools,
        expected_tool_calls=None,
        test_case_context={},
        tool_mode="synthetic",
    )
    assert isinstance(executor, SyntheticToolExecutor)


def test_validate_live_ok_with_webhook_impl() -> None:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_x",
                "parameters": {"type": "object", "properties": {}},
            },
            "platform_config": {
                "implementation": {
                    "type": "http_webhook",
                    "url": "https://example.com/hook",
                },
            },
        },
    ]
    validate_live_tool_snapshot(tools)


def test_validate_live_rejects_missing_platform_config() -> None:
    tools = [
        {
            "type": "function",
            "function": {"name": "bare"},
        },
    ]
    with pytest.raises(ValueError, match="bare"):
        validate_live_tool_snapshot(tools)


def test_validate_live_accepts_legacy_platform_config_with_extra_mode_key() -> None:
    tools = [
        {
            "type": "function",
            "function": {"name": "legacy"},
            "platform_config": {
                "mode": "live",
                "implementation": {
                    "type": "http_webhook",
                    "url": "https://example.com",
                },
            },
        },
    ]
    validate_live_tool_snapshot(tools)


def test_validate_live_empty_tools_noop() -> None:
    validate_live_tool_snapshot([])
    validate_live_tool_snapshot(None)


def test_validate_live_accepts_terminating_tool_without_implementation() -> None:
    validate_live_tool_snapshot([canonical_end_call_tool_dict()])
