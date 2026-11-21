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
        issue_id: str | None = None,
        version: str | None = None,
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
                "issue_id": issue_id,
                "version": version,
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
        version: str | None = None,
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
                "version": version,
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

    def _issue_path(self, workspace_id: str, issue_id: str) -> str:
        return (
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/issues/"
            f"{quote(issue_id, safe='')}"
        )

    async def get_issue(self, *, workspace_id: str, issue_id: str) -> dict[str, Any]:
        return await self._request_json("GET", self._issue_path(workspace_id, issue_id))

    async def archive_issue(
        self, *, workspace_id: str, issue_id: str, reason: str, duration: str
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"{self._issue_path(workspace_id, issue_id)}/archive",
            json={"reason": reason, "duration": duration},
        )

    async def mark_issue_fixed(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        version: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"{self._issue_path(workspace_id, issue_id)}/fixed",
            json={"version": version, "note": note},
        )

    async def unarchive_issue(
        self, *, workspace_id: str, issue_id: str, reason: str | None = None
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"{self._issue_path(workspace_id, issue_id)}/unarchive",
            json={"reason": reason},
        )

    def _spec_path(self, workspace_id: str, agent_id: str) -> str:
        return (
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/agents/"
            f"{quote(agent_id, safe='')}/spec"
        )

    async def get_spec(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        version: int | None = None,
        compare: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if version is not None:
            params["version"] = version
        if compare is not None:
            params["compare"] = compare
        return await self._request_json(
            "GET", self._spec_path(workspace_id, agent_id), params=params
        )

    async def write_spec(
        self, *, workspace_id: str, agent_id: str, rules: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST", self._spec_path(workspace_id, agent_id), json={"rules": rules}
        )

    async def mark_critical_rules(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        critical: list[str],
        not_critical: list[str],
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"{self._spec_path(workspace_id, agent_id)}/critical",
            json={"critical": critical, "not_critical": not_critical},
        )

    async def write_scenarios(
        self, *, workspace_id: str, agent_id: str, scenarios: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/agents/"
            f"{quote(agent_id, safe='')}/scenarios",
            json={"scenarios": scenarios},
        )

    async def list_scenarios(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        rule_key: str | None = None,
        set_name: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params = {
            key: value
            for key, value in {
                "rule_key": rule_key,
                "set": set_name,
                "cursor": cursor,
                "limit": limit,
            }.items()
            if value not in (None, "")
        }
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/agents/"
            f"{quote(agent_id, safe='')}/scenarios",
            params=params,
        )

    async def write_scenario_set(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        name: str,
        scenario_ids: list[str],
        description: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "scenario_ids": scenario_ids}
        if description:
            body["description"] = description
        return await self._request_json(
            "POST",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/agents/"
            f"{quote(agent_id, safe='')}/scenario-sets",
            json=body,
        )

    async def run_scenarios(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        set_name: str | None = None,
        scenario_ids: list[str] | None = None,
        all_scenarios: bool = False,
        repeats: int | None = None,
        version: int | None = None,
        session: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"all": all_scenarios}
        if session is not None:
            body["session"] = session
        if set_name is not None:
            body["set"] = set_name
        if scenario_ids is not None:
            body["scenario_ids"] = scenario_ids
        if repeats is not None:
            body["repeats"] = repeats
        if version is not None:
            body["version"] = version
        return await self._request_json(
            "POST",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/agents/"
            f"{quote(agent_id, safe='')}/test-runs",
            json=body,
        )

    async def get_test_runs(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        run_id: str | None = None,
        version: str | None = None,
        status_only: bool | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params = {
            key: value
            for key, value in {
                "run_id": run_id,
                "version": version,
                "status_only": "true" if status_only else None,
                "cursor": cursor,
                "limit": limit,
            }.items()
            if value not in (None, "")
        }
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/agents/"
            f"{quote(agent_id, safe='')}/test-runs",
            params=params,
        )

    async def raise_clarifications(
        self, *, workspace_id: str, agent_id: str, questions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/agents/"
            f"{quote(agent_id, safe='')}/clarifications",
            json={"questions": questions},
        )

    async def list_clarifications(
        self,
        *,
        workspace_id: str,
        agent_id: str | None = None,
        state: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params = {
            key: value
            for key, value in {
                "agent_id": agent_id,
                "state": state,
                "cursor": cursor,
                "limit": limit,
            }.items()
            if value not in (None, "")
        }
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/clarifications",
            params=params,
        )

    async def answer_clarifications(
        self, *, workspace_id: str, answers: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/clarifications/answers",
            json={"answers": answers},
        )

    async def get_agent(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        period: str | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        params = {
            key: value
            for key, value in {"period": period, "version": version}.items()
            if value not in (None, "")
        }
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/agents/"
            f"{quote(agent_id, safe='')}",
            params=params,
        )

    async def list_categories(self, *, workspace_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET", f"/mcp/workspaces/{quote(workspace_id, safe='')}/categories"
        )

    async def list_tasks(
        self, *, workspace_id: str, cursor: str | None = None, limit: int = 25
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/tasks",
            params=params,
        )

    async def move_task(
        self, *, workspace_id: str, key: str, before: str | None = None
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/tasks/move",
            json={"key": key, "before": before},
        )

    async def get_next_task(
        self, *, workspace_id: str, session: str | None = None
    ) -> dict[str, Any]:
        params = {"session": session} if session else None
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/next-task",
            params=params,
        )

    async def get_readiness(self, *, workspace_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET", f"/mcp/workspaces/{quote(workspace_id, safe='')}/readiness"
        )

    async def get_dashboard(
        self,
        *,
        workspace_id: str,
        agent_id: str | None = None,
        period: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {}
        if agent_id:
            params["agent_id"] = agent_id
        if period:
            params["period"] = period
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/dashboard",
            params=params,
        )

    async def get_usage(
        self,
        *,
        workspace_id: str,
        agent_id: str | None = None,
        period: str | None = None,
        month: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {}
        if agent_id:
            params["agent_id"] = agent_id
        if period:
            params["period"] = period
        if month:
            params["month"] = month
        if cursor:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        return await self._request_json(
            "GET",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/usage",
            params=params,
        )

    async def send_feedback(
        self,
        *,
        workspace_id: str,
        kind: str,
        title: str,
        what_happened: str | None = None,
        wanted: str | None = None,
        tool: str | None = None,
        error: str | None = None,
        ids: list[str] | None = None,
        session: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"kind": kind, "title": title}
        for key, value in {
            "what_happened": what_happened,
            "wanted": wanted,
            "tool": tool,
            "error": error,
            "ids": ids,
            "session": session,
        }.items():
            if value not in (None, "", []):
                body[key] = value
        return await self._request_json(
            "POST",
            f"/mcp/workspaces/{quote(workspace_id, safe='')}/feedback",
            json=body,
        )

    async def list_agents(
        self,
        *,
        workspace_id: str,
        query: str | None = None,
        period: str | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {"limit": limit}
        if query:
            params["query"] = query
        if period:
            params["period"] = period
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
            # Not on send_feedback's own failure: it cannot report itself.
            if exc.response.status_code >= 500 and not path.endswith("/feedback"):
                detail = f"{detail} {REPORT_HINT}"
            raise ConnexityBackendError(detail) from exc
        except httpx.HTTPError as exc:
            hint = "" if path.endswith("/feedback") else f" {REPORT_HINT}"
            raise ConnexityBackendError(
                f"Connexity backend request failed: {exc}{hint}"
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


# Added to Connexity's own failures, so an assistant that never read the feedback guide
# still finds where to report them (plan `plans/2026-11-19-assistant-feedback.md`).
REPORT_HINT = (
    "This is a problem in Connexity, not in your request: retry once, and if it fails "
    "again, report it with `send_feedback` (kind bug, with this tool and error)."
)


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
