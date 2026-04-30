"""Custom metric CRUD plus LLM-backed metric preview generation."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class CustomMetricsApi(_BaseApi):
    """``/custom-metrics/*`` endpoints."""

    def list(self, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._t.get_dict("custom-metrics/", params=params)

    def get(self, metric_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"custom-metrics/{metric_id}")

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("custom-metrics/", json_body=body)

    def update(self, metric_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.put_dict(f"custom-metrics/{metric_id}", json_body=body)

    def delete(self, metric_id: str) -> dict[str, Any]:
        return self._t.delete_dict(f"custom-metrics/{metric_id}")

    def generate(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("custom-metrics/generate", json_body=body)
