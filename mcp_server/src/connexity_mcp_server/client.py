from __future__ import annotations

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
        self._token = (
            settings.connexity_api_token.strip()
            if isinstance(settings.connexity_api_token, str)
            and settings.connexity_api_token.strip()
            else None
        )
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
            f"/agents/{agent_id}/draft",
            json={"system_prompt": system_prompt},
        )

    async def list_agents(self, skip: int = 0, limit: int = 100) -> dict[str, Any]:
        return await self._request_json(
            "GET",
            "/agents",
            params={"skip": skip, "limit": limit},
        )

    async def get_agent_draft(self, agent_id: str) -> dict[str, Any]:
        return await self._request_json("GET", f"/agents/{agent_id}/draft")

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
        if self._token:
            return self._token

        saved_token = self._settings.load_saved_cli_token()
        if saved_token:
            self._token = saved_token
            return self._token

        email = self._settings.connexity_email or self._settings.dev_email
        password = self._settings.connexity_password or self._settings.dev_password
        if email and password:
            self._token = await self._login_for_token(email=email, password=password)
            return self._token

        raise ConnexityBackendError(
            "Connexity auth is not configured. Provide CONNEXITY_API_TOKEN, or save "
            "CLI credentials with connexity-cli login --save, or set CONNEXITY_EMAIL "
            "and CONNEXITY_PASSWORD for dev login."
        )

    async def _login_for_token(self, *, email: str, password: str) -> str:
        try:
            response = await self._client.post(
                f"{self._settings.normalized_api_url}/login/access-token",
                headers={"Accept": "application/json"},
                data={"username": email, "password": password},
                follow_redirects=True,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ConnexityBackendError(
                    "Connexity login returned a non-object JSON payload."
                )
            token = payload.get("access_token")
            if not isinstance(token, str) or not token.strip():
                raise ConnexityBackendError(
                    "Connexity login response did not include access_token."
                )
            return token.strip()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            raise ConnexityBackendError(f"Connexity login failed: {detail}") from exc
        except httpx.HTTPError as exc:
            raise ConnexityBackendError(f"Connexity login failed: {exc}") from exc


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
