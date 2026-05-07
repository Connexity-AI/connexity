from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.webhook_deploy import deliver_webhook_deployment


@pytest.mark.asyncio
async def test_deliver_webhook_deployment_accepts_2xx() -> None:
    response = httpx.Response(
        status_code=204,
        request=httpx.Request("POST", "https://example.com/hooks/deploy"),
    )
    with patch("app.services.webhook_deploy.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = response
        mock_client_cls.return_value = mock_client

        result = await deliver_webhook_deployment(
            endpoint_url="https://example.com/hooks/deploy",
            payload={"event": "agent.deploy"},
        )
    assert result.success is True
    assert result.error_message is None


@pytest.mark.asyncio
async def test_deliver_webhook_deployment_returns_response_body_on_error() -> None:
    response = httpx.Response(
        status_code=500,
        text="upstream exploded",
        request=httpx.Request("POST", "https://example.com/hooks/deploy"),
    )
    with patch("app.services.webhook_deploy.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = response
        mock_client_cls.return_value = mock_client

        result = await deliver_webhook_deployment(
            endpoint_url="https://example.com/hooks/deploy",
            payload={"event": "agent.deploy"},
        )
    assert result.success is False
    assert result.error_message is not None
    assert "500" in result.error_message
    assert "upstream exploded" in result.error_message


@pytest.mark.asyncio
async def test_deliver_webhook_deployment_encodes_datetime_payload_values() -> None:
    response = httpx.Response(
        status_code=200,
        request=httpx.Request("POST", "https://example.com/hooks/deploy"),
    )
    with patch("app.services.webhook_deploy.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = response
        mock_client_cls.return_value = mock_client

        run_at = datetime(2026, 5, 7, 7, 30, tzinfo=UTC)
        result = await deliver_webhook_deployment(
            endpoint_url="https://example.com/hooks/deploy",
            payload={"event": "agent.deploy", "eval": {"run_at": run_at}},
        )

    assert result.success is True
    assert result.error_message is None
    posted_json = mock_client.post.call_args.kwargs["json"]
    assert posted_json["eval"]["run_at"] == "2026-05-07T07:30:00+00:00"
