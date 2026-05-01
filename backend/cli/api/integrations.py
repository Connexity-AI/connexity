"""Third-party integrations (Retell etc.)."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class IntegrationsApi(_BaseApi):
    """``/integrations/*`` endpoints."""

    def list(self, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._t.get_dict("integrations/", params=params)

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("integrations/", json_body=body)

    def delete(self, integration_id: str) -> dict[str, Any]:
        return self._t.delete_dict(f"integrations/{integration_id}")

    def test(self, integration_id: str) -> dict[str, Any]:
        return self._t.post_dict(f"integrations/{integration_id}/test")

    def list_agents(self, integration_id: str) -> list[Any]:
        return self._t.get_list(f"integrations/{integration_id}/agents")
