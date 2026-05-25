from __future__ import annotations

from typing import Any

import httpx
from mcp.server.auth.middleware.auth_context import get_access_token

from connexity_mcp_server.config import Settings


class ConnexityBackendError(RuntimeError):
    """Raised when the Connexity backend request fails."""


class ConnexityBackendClient:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._client = http_client or httpx.AsyncClient(
            base_url=settings.normalized_api_url,
            timeout=settings.connexity_api_timeout_seconds,
            follow_redirects=True,
        )
        self._owns_client = http_client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def update_agent_draft(self, agent_id: str, system_prompt: str) -> dict[str, Any]:
        return await self._request_json(
            "PUT",
            f"/mcp/agents/{agent_id}/draft",
            json={"system_prompt": system_prompt},
        )

    async def list_agents(self, skip: int = 0, limit: int = 100) -> dict[str, Any]:
        return await self._request_json(
            "GET",
            "/mcp/agents",
            params={"skip": skip, "limit": limit},
        )

    async def get_agent_draft(self, agent_id: str) -> dict[str, Any]:
        return await self._request_json("GET", f"/mcp/agents/{agent_id}/draft")

    async def _request_json(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        headers = await self._build_headers()
        custom_headers = kwargs.pop("headers", None)
        if isinstance(custom_headers, dict):
            headers.update(custom_headers)

        try:
            response = await self._client.request(
                method,
                f"{self._settings.normalized_api_url}{path}",
                headers=headers,
                follow_redirects=True,
                **kwargs,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ConnexityBackendError(
                    "Connexity backend returned a non-object JSON payload."
                )
            return payload
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            raise ConnexityBackendError(
                f"Connexity backend request failed: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ConnexityBackendError(
                f"Connexity backend request failed: {exc}"
            ) from exc

    async def _build_headers(self) -> dict[str, str]:
        headers = dict(self._default_headers)
        access_token = get_access_token()
        if access_token is None or not access_token.token.strip():
            raise ConnexityBackendError(
                "Connexity backend requests require an authenticated MCP user."
            )
        headers["Authorization"] = f"Bearer {access_token.token}"
        return headers


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text or f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    return f"HTTP {response.status_code}"
