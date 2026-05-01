"""Authentication endpoints (login / logout / token validation)."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class AuthApi(_BaseApi):
    """``/login/*`` and ``/logout`` endpoints."""

    def login(self, *, email: str, password: str) -> dict[str, Any]:
        """Exchange email + password for a JWT access token.

        Wraps ``POST /login/access-token`` (OAuth2 password form).
        """
        return self._t.post_form_dict(
            "login/access-token",
            data={"username": email, "password": password},
        )

    def test_token(self) -> dict[str, Any]:
        """Validate the current bearer token; returns the authenticated user."""
        return self._t.post_dict("login/test-token")

    def logout(self) -> dict[str, Any]:
        """Best-effort server-side logout (clears auth cookie if any)."""
        return self._t.post_dict("logout")

    def recover_password(self, email: str) -> dict[str, Any]:
        return self._t.post_dict(f"password-recovery/{email}")

    def reset_password(self, *, token: str, new_password: str) -> dict[str, Any]:
        return self._t.post_dict(
            "reset-password/",
            json_body={"token": token, "new_password": new_password},
        )
