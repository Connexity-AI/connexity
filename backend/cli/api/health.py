"""Top-level health endpoint."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class HealthApi(_BaseApi):
    """``GET /`` health probe."""

    def check(self) -> dict[str, Any]:
        # The health route is mounted at the root of the API prefix ("/"),
        # which httpx resolves to the base URL when the path is empty.
        return self._t.get_dict("")
