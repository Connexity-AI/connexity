"""Eval config CRUD and member management."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class EvalConfigsApi(_BaseApi):
    """``/eval-configs/*`` endpoints."""

    def list(self, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._t.get_dict("eval-configs/", params=params)

    def get(self, eval_config_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"eval-configs/{eval_config_id}")

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("eval-configs/", json_body=body)

    def update(self, eval_config_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.patch_dict(f"eval-configs/{eval_config_id}", json_body=body)

    def delete(self, eval_config_id: str) -> dict[str, Any]:
        return self._t.delete_dict(f"eval-configs/{eval_config_id}")

    # --- members ----------------------------------------------------------

    def list_members(
        self, eval_config_id: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self._t.get_dict(
            f"eval-configs/{eval_config_id}/test-cases", params=params
        )

    def add_members(self, eval_config_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict(
            f"eval-configs/{eval_config_id}/test-cases", json_body=body
        )

    def replace_members(
        self, eval_config_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        return self._t.put_dict(
            f"eval-configs/{eval_config_id}/test-cases", json_body=body
        )

    def remove_member(self, eval_config_id: str, test_case_id: str) -> dict[str, Any]:
        return self._t.delete_dict(
            f"eval-configs/{eval_config_id}/test-cases/{test_case_id}"
        )
