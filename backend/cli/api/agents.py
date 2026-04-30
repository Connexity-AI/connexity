"""Agent CRUD, draft/publish/rollback, versions, guidelines."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class AgentsApi(_BaseApi):
    """``/agents/*`` endpoints."""

    # --- CRUD -------------------------------------------------------------

    def list(self, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._t.get_dict("agents/", params=params)

    def get(self, agent_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"agents/{agent_id}")

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("agents/", json_body=body)

    def create_draft(self, *, name: str) -> dict[str, Any]:
        return self._t.post_dict("agents/draft", json_body={"name": name})

    def update(self, agent_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.patch_dict(f"agents/{agent_id}", json_body=body)

    def delete(self, agent_id: str) -> dict[str, Any]:
        return self._t.delete_dict(f"agents/{agent_id}")

    # --- draft & publish --------------------------------------------------

    def get_draft(self, agent_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"agents/{agent_id}/draft")

    def upsert_draft(self, agent_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.put_dict(f"agents/{agent_id}/draft", json_body=body)

    def discard_draft(self, agent_id: str) -> None:
        self._t.delete_any(f"agents/{agent_id}/draft")

    def publish(
        self, agent_id: str, *, change_description: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if change_description is not None:
            body["change_description"] = change_description
        return self._t.post_dict(f"agents/{agent_id}/publish", json_body=body)

    def rollback(
        self,
        agent_id: str,
        *,
        version: int,
        change_description: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"version": version}
        if change_description is not None:
            body["change_description"] = change_description
        return self._t.post_dict(f"agents/{agent_id}/rollback", json_body=body)

    # --- versions ---------------------------------------------------------

    def list_versions(
        self, agent_id: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self._t.get_dict(f"agents/{agent_id}/versions", params=params)

    def get_version(self, agent_id: str, version: int) -> dict[str, Any]:
        return self._t.get_dict(f"agents/{agent_id}/versions/{version}")

    def diff_versions(
        self, agent_id: str, *, from_version: int, to_version: int
    ) -> dict[str, Any]:
        return self._t.get_dict(
            f"agents/{agent_id}/versions/diff",
            params={"from_version": from_version, "to_version": to_version},
        )

    # --- guidelines -------------------------------------------------------

    def get_guidelines(self, agent_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"agents/{agent_id}/guidelines")

    def put_guidelines(self, agent_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.put_dict(f"agents/{agent_id}/guidelines", json_body=body)
