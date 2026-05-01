"""Run CRUD, lifecycle, baselines, comparison, and SSE streaming."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from httpx_sse import ServerSentEvent

from cli.api._base import _BaseApi


class RunsApi(_BaseApi):
    """``/runs/*`` endpoints."""

    # --- CRUD -------------------------------------------------------------

    def list(self, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._t.get_dict("runs/", params=params)

    def get(self, run_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"runs/{run_id}")

    def create(
        self, body: dict[str, Any], *, auto_execute: bool = True
    ) -> dict[str, Any]:
        return self._t.post_dict(
            "runs/",
            params={"auto_execute": "true" if auto_execute else "false"},
            json_body=body,
        )

    def update(self, run_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.patch_dict(f"runs/{run_id}", json_body=body)

    def delete(self, run_id: str) -> dict[str, Any]:
        return self._t.delete_dict(f"runs/{run_id}")

    # --- lifecycle --------------------------------------------------------

    def execute(self, run_id: str) -> dict[str, Any]:
        return self._t.post_dict(f"runs/{run_id}/execute")

    def cancel(self, run_id: str) -> dict[str, Any]:
        return self._t.post_dict(f"runs/{run_id}/cancel")

    def stream(self, run_id: str) -> Iterator[ServerSentEvent]:
        yield from self._t.stream_sse("GET", f"runs/{run_id}/stream")

    # --- baselines / comparison ------------------------------------------

    def get_baseline(
        self,
        *,
        agent_id: str,
        eval_config_id: str,
        agent_version: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "agent_id": agent_id,
            "eval_config_id": eval_config_id,
        }
        if agent_version is not None:
            params["agent_version"] = agent_version
        return self._t.get_dict("runs/baseline", params=params)

    def compare(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._t.get_dict("runs/compare", params=params)

    def compare_suggestions(
        self, *, baseline_run_id: str, candidate_run_id: str
    ) -> dict[str, Any]:
        return self._t.post_dict(
            "runs/compare/suggestions",
            json_body={
                "baseline_run_id": baseline_run_id,
                "candidate_run_id": candidate_run_id,
            },
        )
