from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.retell import (
    _map_tools_for_retell,
    create_retell_agent_playground_completion,
)


def _response(
    method: str, url: str, *, status_code: int = 200, json=None
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json,
        request=httpx.Request(method, url),
    )


def test_map_tools_for_retell_includes_native_end_call() -> None:
    mapped = _map_tools_for_retell(
        [
            {
                "type": "function",
                "function": {
                    "name": "end_call",
                    "description": "End the call cleanly.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
                "platform_config": {
                    "predefined": True,
                    "terminating": True,
                },
            }
        ]
    )

    assert mapped == [
        {
            "type": "end_call",
            "name": "end_call",
            "description": "End the call cleanly.",
        }
    ]


@pytest.mark.asyncio
async def test_playground_completion_retries_after_429_and_succeeds() -> None:
    with (
        patch("app.services.retell.httpx.AsyncClient") as mock_client_cls,
        patch("app.services.retell.asyncio.sleep", new=AsyncMock()) as mock_sleep,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [
            _response(
                "POST",
                "https://api.retellai.com/agent-playground-completion/agent_123",
                status_code=429,
                json={
                    "status": "error",
                    "message": "Too many API requests, you are being throttled",
                },
            ),
            _response(
                "POST",
                "https://api.retellai.com/agent-playground-completion/agent_123",
                json={
                    "messages": [{"role": "agent", "content": "Hello there"}],
                    "current_state": "collect_issue",
                    "dynamic_variables": {"customer_name": "Avery"},
                },
            ),
        ]
        mock_client_cls.return_value = mock_client

        result = await create_retell_agent_playground_completion(
            api_key="retell-key",
            retell_agent_id="agent_123",
            messages=[{"role": "user", "content": "Hi"}],
        )

    assert result.success is True
    assert [m.content for m in result.messages] == ["Hello there"]
    assert result.current_state == "collect_issue"
    assert result.dynamic_variables == {"customer_name": "Avery"}
    assert mock_client.post.await_count == 2
    mock_sleep.assert_awaited_once_with(1.0)


@pytest.mark.asyncio
async def test_playground_completion_returns_error_after_exhausting_429_retries() -> (
    None
):
    throttled = _response(
        "POST",
        "https://api.retellai.com/agent-playground-completion/agent_123",
        status_code=429,
        json={
            "status": "error",
            "message": "Too many API requests, you are being throttled",
        },
    )
    with (
        patch("app.services.retell.httpx.AsyncClient") as mock_client_cls,
        patch("app.services.retell.asyncio.sleep", new=AsyncMock()) as mock_sleep,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [throttled, throttled, throttled, throttled]
        mock_client_cls.return_value = mock_client

        result = await create_retell_agent_playground_completion(
            api_key="retell-key",
            retell_agent_id="agent_123",
            messages=[{"role": "user", "content": "Hi"}],
        )

    assert result.success is False
    assert "returned 429" in (result.error_message or "")
    assert mock_client.post.await_count == 4
    assert mock_sleep.await_count == 3
