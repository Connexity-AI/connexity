"""Test-case CRUD, import/export, generate, and AI agent."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class TestCasesApi(_BaseApi):
    """``/test-cases/*`` endpoints."""

    # --- CRUD -------------------------------------------------------------

    def list(self, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._t.get_dict("test-cases/", params=params)

    def get(self, test_case_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"test-cases/{test_case_id}")

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("test-cases/", json_body=body)

    def update(self, test_case_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.patch_dict(f"test-cases/{test_case_id}", json_body=body)

    def delete(self, test_case_id: str) -> dict[str, Any]:
        return self._t.delete_dict(f"test-cases/{test_case_id}")

    # --- bulk -------------------------------------------------------------

    def import_(
        self,
        items: list[dict[str, Any]],
        *,
        on_conflict: str = "skip",
    ) -> dict[str, Any]:
        return self._t.post_dict(
            "test-cases/import",
            params={"on_conflict": on_conflict},
            json_body=items,
        )

    def export(self, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._t.get_dict("test-cases/export", params=params)

    # --- generation / AI --------------------------------------------------

    def generate(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("test-cases/generate", json_body=body)

    def ai(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("test-cases/ai", json_body=body)
