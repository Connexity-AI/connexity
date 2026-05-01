"""Per-test-case run result CRUD."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class TestCaseResultsApi(_BaseApi):
    """``/test-case-results/*`` endpoints."""

    def list(self, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._t.get_dict("test-case-results/", params=params)

    def get(self, result_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"test-case-results/{result_id}")

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("test-case-results/", json_body=body)

    def update(self, result_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.patch_dict(f"test-case-results/{result_id}", json_body=body)

    def delete(self, result_id: str) -> dict[str, Any]:
        return self._t.delete_dict(f"test-case-results/{result_id}")
