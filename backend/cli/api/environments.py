"""Agent deployment environments (e.g. Retell agent bindings)."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class EnvironmentsApi(_BaseApi):
    """``/environments/*`` endpoints."""

    def list(self, *, agent_id: str) -> dict[str, Any]:
        return self._t.get_dict("environments/", params={"agent_id": agent_id})

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("environments/", json_body=body)

    def delete(self, environment_id: str) -> dict[str, Any]:
        return self._t.delete_dict(f"environments/{environment_id}")

    def deploy(self, environment_id: str, *, agent_version: int) -> dict[str, Any]:
        return self._t.post_dict(
            f"environments/{environment_id}/deploy",
            json_body={"agent_version": agent_version},
        )

    def retell_versions(self, environment_id: str) -> list[Any]:
        return self._t.get_list(f"environments/{environment_id}/retell-versions")

    def list_agent_deployments(self, *, agent_id: str) -> dict[str, Any]:
        return self._t.get_dict(
            "environments/deployments", params={"agent_id": agent_id}
        )

    def list_environment_deployments(self, environment_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"environments/{environment_id}/deployments")
