"""User self-service endpoints (``/users/me`` family)."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class UsersApi(_BaseApi):
    """``/users/*`` endpoints."""

    def me(self) -> dict[str, Any]:
        return self._t.get_dict("users/me")

    def update_me(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.patch_dict("users/me", json_body=body)

    def update_password(
        self, *, current_password: str, new_password: str
    ) -> dict[str, Any]:
        return self._t.patch_dict(
            "users/me/password",
            json_body={
                "current_password": current_password,
                "new_password": new_password,
            },
        )

    def delete_me(self) -> dict[str, Any]:
        return self._t.delete_dict("users/me")

    def signup(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("users/signup", json_body=body)
