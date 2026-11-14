from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx
from mcp.server.auth.middleware.auth_context import get_access_token

from connexity_mcp_server.config import Settings


# A scan step works for about 40 seconds, past that only to finish a page or to count
# a large window.
SCAN_TIMEOUT_SECONDS = 180.0


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

    async def list_workspaces(self) -> dict[str, Any]:
        return await self._request_json("GET", "/mcp/workspaces")

    async def create_workspace(self, *, name: str) -> dict[str, Any]:
        return await self._request_json("POST", "/mcp/workspaces", json={"name": name})

    async def connect_voice_platform(
        self, *, workspace_id: str, platform: str, api_key: str
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/connections",
            json={"platform": platform, "api_key": api_key},
        )

    async def add_agents(
        self, *, workspace_id: str, agents: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/agents",
            json={"agents": agents},
        )

    async def scan_calls(self, *, workspace_id: str) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/scan",
            timeout=SCAN_TIMEOUT_SECONDS,
        )

    async def get_call(self, *, workspace_id: str, call_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/calls/"
            f"{quote(call_id, safe='')}",
        )

    async def list_calls(
        self,
        *,
        workspace_id: str,
        query: str | None = None,
        agent_id: str | None = None,
        result: str | None = None,
        category: str | None = None,
        period: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params = {
            key: value
            for key, value in {
                "query": query,
                "agent_id": agent_id,
                "result": result,
                "category": category,
                "period": period,
                "cursor": cursor,
                "limit": limit,
            }.items()
            if value not in (None, "")
        }
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/calls",
            params=params,
        )

    async def list_issues(
        self,
        *,
        workspace_id: str,
        query: str | None = None,
        agent_id: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        period: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params = {
            key: value
            for key, value in {
                "query": query,
                "agent_id": agent_id,
                "category": category,
                "severity": severity,
                "status": status,
                "period": period,
                "cursor": cursor,
                "limit": limit,
            }.items()
            if value not in (None, "")
        }
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/issues",
            params=params,
        )

    async def list_categories(self, *, workspace_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET", f"/mcp/workspaces/{quote(workspace_id, safe='')}/categories"
        )

    async def get_readiness(self, *, workspace_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET", f"/mcp/workspaces/{quote(workspace_id, safe='')}/readiness"
        )

    async def list_agents(
        self,
        *,
        workspace_id: str,
        query: str | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {"limit": limit}
        if query:
            params["query"] = query
        if cursor:
            params["cursor"] = cursor
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/agents",
            params=params,
        )

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
            raise ConnexityBackendError(detail) from exc
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
        if isinstance(detail, dict):
            return _format_answer_error(detail) or f"HTTP {response.status_code}"
        if isinstance(detail, list):
            return _format_validation_error(detail)
    return f"HTTP {response.status_code}"


def _format_validation_error(errors: list[Any]) -> str:
    """FastAPI's 422 list of invalid arguments, as text the assistant can act on."""
    problems = []
    for item in errors:
        if not isinstance(item, dict):
            continue
        loc = item.get("loc")
        name = loc[-1] if isinstance(loc, list) and loc else "argument"
        problems.append(f"`{name}`: {item.get('msg', 'invalid')}")
    summary = "; ".join(problems) or "an argument is not valid"
    return (
        _format_answer_error(
            {
                "error": f"Invalid arguments ({summary})",
                "next_steps": [
                    "Fix the arguments and call the tool again. A `workspace_id` is an "
                    "`id` returned by `list_workspaces`."
                ],
                "guide": "connexity://guides/getting-started",
            }
        )
        or "Invalid arguments"
    )


def _format_answer_error(detail: dict[str, Any]) -> str | None:
    """An error in the standard shape, as text the assistant can act on."""
    error = detail.get("error")
    if not isinstance(error, str) or not error.strip():
        return None
    message = error.strip()
    parts = [message if message.endswith((".", "?", "!")) else f"{message}."]
    steps = [s for s in detail.get("next_steps") or [] if isinstance(s, str)]
    if steps:
        numbered = " ".join(f"{i}. {step}" for i, step in enumerate(steps, start=1))
        parts.append(f"Next steps: {numbered}")
    guide = detail.get("guide")
    if isinstance(guide, str) and guide:
        parts.append(f"Guide: {guide}")
    return " ".join(parts)
