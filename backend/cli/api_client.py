"""HTTP client for the Connexity Evals REST API (used by the CLI only)."""

import json
from collections.abc import Iterator
from typing import Any, Self

import click
import httpx
from httpx_sse import EventSource, ServerSentEvent

DEFAULT_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


class ApiClient:
    """Sync httpx client with Bearer auth and JSON helpers."""

    def __init__(self, base_url: str, token: str) -> None:
        root = base_url.rstrip("/")
        api_root = f"{root}{API_PREFIX}/"
        headers: dict[str, str] = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(base_url=api_root, headers=headers, timeout=600.0)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            raw = response.json()
            if not isinstance(raw, dict):
                detail = response.text
            else:
                body = raw
                detail = body.get("detail", response.text)
            if isinstance(detail, list):
                detail = json.dumps(detail)
        except (json.JSONDecodeError, ValueError):
            detail = response.text or response.reason_phrase
        raise click.ClickException(f"API error {response.status_code}: {detail}")

    def _json_dict(self, response: httpx.Response) -> dict[str, Any]:
        self._raise_for_status(response)
        data = response.json()
        if not isinstance(data, dict):
            raise click.ClickException("Expected a JSON object from the API")
        return data

    def create_run(
        self, body: dict[str, Any], *, auto_execute: bool = True
    ) -> dict[str, Any]:
        r = self._client.post(
            "runs/",
            params={"auto_execute": "true" if auto_execute else "false"},
            json=body,
        )
        return self._json_dict(r)

    def get_run(self, run_id: str) -> dict[str, Any]:
        r = self._client.get(f"runs/{run_id}")
        return self._json_dict(r)

    def update_run(self, run_id: str, body: dict[str, Any]) -> dict[str, Any]:
        r = self._client.patch(f"runs/{run_id}", json=body)
        return self._json_dict(r)

    def list_runs(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self._client.get("runs/", params=params or {})
        return self._json_dict(r)

    def get_baseline_run(self, agent_id: str, scenario_set_id: str) -> dict[str, Any]:
        r = self._client.get(
            "runs/baseline",
            params={"agent_id": agent_id, "scenario_set_id": scenario_set_id},
        )
        return self._json_dict(r)

    def list_scenarios(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self._client.get("scenarios/", params=params or {})
        return self._json_dict(r)

    def import_scenarios(
        self,
        items: list[dict[str, Any]],
        *,
        on_conflict: str = "skip",
    ) -> dict[str, Any]:
        r = self._client.post(
            "scenarios/import",
            params={"on_conflict": on_conflict},
            json=items,
        )
        return self._json_dict(r)

    def export_scenarios(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self._client.get("scenarios/export", params=params or {})
        return self._json_dict(r)

    def generate_scenarios(self, body: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("scenarios/generate", json=body)
        return self._json_dict(r)

    def compare_runs(self, params: dict[str, Any]) -> dict[str, Any]:
        r = self._client.get("runs/compare", params=params)
        return self._json_dict(r)

    def list_agents(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self._client.get("agents/", params=params or {})
        return self._json_dict(r)

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        r = self._client.get(f"agents/{agent_id}")
        return self._json_dict(r)

    def list_scenario_sets(
        self, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        r = self._client.get("scenario-sets/", params=params or {})
        return self._json_dict(r)

    def get_scenario_set(self, scenario_set_id: str) -> dict[str, Any]:
        r = self._client.get(f"scenario-sets/{scenario_set_id}")
        return self._json_dict(r)

    def iter_run_sse(self, run_id: str) -> Iterator[ServerSentEvent]:
        with self._client.stream("GET", f"runs/{run_id}/stream") as response:
            self._raise_for_status(response)
            yield from EventSource(response).iter_sse()
