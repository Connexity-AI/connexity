from __future__ import annotations

import time
from typing import Any

import httpx

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
        self._token: str | None = None
        self._token_expires_at = 0.0
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
        token = await self._get_auth_token()
        headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _get_auth_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        client_id = self._settings.resolved_mcp_client_id
        client_secret = (
            self._settings.mcp_client_secret.strip()
            if isinstance(self._settings.mcp_client_secret, str)
            else ""
        )
        if not client_secret:
            raise ConnexityBackendError(
                "Connexity service auth is not configured. Provide "
                "MCP_CLIENT_SECRET."
            )

        try:
            response = await self._client.request(
                "POST",
                f"{self._settings.normalized_api_url}/internal/token",
                headers=self._default_headers,
                json={"client_id": client_id, "client_secret": client_secret},
                follow_redirects=True,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            raise ConnexityBackendError(
                f"Connexity service auth failed: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ConnexityBackendError(
                f"Connexity service auth failed: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise ConnexityBackendError(
                "Connexity service auth returned a non-object JSON payload."
            )

        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not isinstance(access_token, str) or not access_token.strip():
            raise ConnexityBackendError(
                "Connexity service auth response did not include a valid access token."
            )
        if not isinstance(expires_in, int) or expires_in <= 0:
            raise ConnexityBackendError(
                "Connexity service auth response did not include a valid expires_in."
            )

        self._token = access_token.strip()
        self._token_expires_at = time.monotonic() + max(expires_in - 30, 0)
        return self._token


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
