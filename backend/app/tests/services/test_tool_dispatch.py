"""Tests for :mod:`app.services.tool_dispatch` — mock, live, and composite routing."""

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
from app.services.tool_dispatch import (
    CompositeToolExecutor,
    LiveToolExecutor,
    MockToolExecutor,
    build_tool_executor,
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
            mode="live",
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
            mode="live",
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


# ── CompositeToolExecutor ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_composite_routes_mock_and_live() -> None:
    mock_exec = MockToolExecutor(
        [
            ExpectedToolCall(
                tool="check_balance",
                mock_responses=[MockResponse(response={"balance": 100})],
            ),
        ]
    )
    live_exec = AsyncMock(spec=LiveToolExecutor)
    live_exec.execute = AsyncMock(return_value=json.dumps({"notified": True}))

    composite = CompositeToolExecutor(
        tool_modes={"check_balance": "mock", "notify": "live"},
        mock=mock_exec,
        live=live_exec,
    )

    r_mock = json.loads(await composite.execute("check_balance", "c1", "{}"))
    assert r_mock == {"balance": 100}

    r_live = json.loads(await composite.execute("notify", "c2", "{}"))
    assert r_live == {"notified": True}
    live_exec.execute.assert_awaited_once_with("notify", "c2", "{}")


@pytest.mark.asyncio
async def test_composite_unknown_tool_falls_back_to_synthetic() -> None:
    composite = CompositeToolExecutor(
        tool_modes={},
        mock=MockToolExecutor([]),
        live=LiveToolExecutor({}, {}),
    )
    result = json.loads(await composite.execute("unknown", "c1", "{}"))
    assert result.get("status") == "simulated"


# ── build_tool_executor ───────────────────────────────────────────


def test_build_no_tools_returns_synthetic() -> None:
    executor = build_tool_executor(
        tools=None, expected_tool_calls=None, test_case_context={}
    )
    assert isinstance(executor, SyntheticToolExecutor)


def test_build_no_platform_config_returns_synthetic() -> None:
    tools = [
        {
            "type": "function",
            "function": {"name": "search", "parameters": {}},
        }
    ]
    executor = build_tool_executor(
        tools=tools, expected_tool_calls=None, test_case_context={}
    )
    assert isinstance(executor, SyntheticToolExecutor)


def test_build_mixed_modes_returns_composite() -> None:
    tools = [
        {
            "type": "function",
            "function": {"name": "lookup"},
            "platform_config": {"mode": "mock"},
        },
        {
            "type": "function",
            "function": {"name": "compute"},
            "platform_config": {
                "mode": "live",
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
        tools=tools, expected_tool_calls=expected, test_case_context={"key": "val"}
    )
    assert isinstance(executor, CompositeToolExecutor)
