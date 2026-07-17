from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.retell import check_retell_flow_staleness


def _response(
    method: str, url: str, *, status_code: int = 200, json=None
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json,
        request=httpx.Request(method, url),
    )


def _mock_client_returning(response: httpx.Response):
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = response
    return mock_client


@pytest.mark.asyncio
async def test_stale_when_live_version_is_newer() -> None:
    with patch("app.services.retell.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value = _mock_client_returning(
            _response(
                "GET",
                "https://api.retellai.com/get-conversation-flow/flow_1",
                json={"conversation_flow_id": "flow_1", "version": 5},
            )
        )
        is_stale, live_version = await check_retell_flow_staleness(
            api_key="key", conversation_flow_id="flow_1", captured_version=3
        )

    assert is_stale is True
    assert live_version == 5


@pytest.mark.asyncio
async def test_not_stale_when_versions_match() -> None:
    with patch("app.services.retell.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value = _mock_client_returning(
            _response(
                "GET",
                "https://api.retellai.com/get-conversation-flow/flow_1",
                json={"conversation_flow_id": "flow_1", "version": 3},
            )
        )
        is_stale, live_version = await check_retell_flow_staleness(
            api_key="key", conversation_flow_id="flow_1", captured_version=3
        )

    assert is_stale is False
    assert live_version == 3


@pytest.mark.asyncio
async def test_not_stale_when_captured_version_missing() -> None:
    """Legacy imports with no captured version never claim staleness."""
    with patch("app.services.retell.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value = _mock_client_returning(
            _response(
                "GET",
                "https://api.retellai.com/get-conversation-flow/flow_1",
                json={"conversation_flow_id": "flow_1", "version": 7},
            )
        )
        is_stale, live_version = await check_retell_flow_staleness(
            api_key="key", conversation_flow_id="flow_1", captured_version=None
        )

    assert is_stale is False
    assert live_version == 7


@pytest.mark.asyncio
async def test_not_stale_on_retell_api_failure() -> None:
    """A transient Retell error is an informational no-op, not a hard failure."""
    with patch("app.services.retell.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value = _mock_client_returning(
            _response(
                "GET",
                "https://api.retellai.com/get-conversation-flow/flow_1",
                status_code=500,
            )
        )
        is_stale, live_version = await check_retell_flow_staleness(
            api_key="key", conversation_flow_id="flow_1", captured_version=3
        )

    assert is_stale is False
    assert live_version is None
