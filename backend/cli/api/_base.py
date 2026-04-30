"""Shared HTTP transport + JSON helpers for the resource-namespaced ApiClient.

Each resource module (``agents.py``, ``runs.py``, …) holds a reference to a
single ``_Transport`` so we share one ``httpx.Client`` and one error-mapping
implementation across the whole CLI.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import click
import httpx
from httpx_sse import EventSource, ServerSentEvent

DEFAULT_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
DEFAULT_TIMEOUT_SECONDS = 600.0


class _Transport:
    """Sync httpx wrapper with Bearer auth and JSON helpers (internal)."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        root = base_url.rstrip("/")
        api_root = f"{root}{API_PREFIX}/"
        headers: dict[str, str] = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(base_url=api_root, headers=headers, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    @property
    def http(self) -> httpx.Client:
        return self._client

    # --- error mapping ----------------------------------------------------

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            raw = response.json()
            if isinstance(raw, dict):
                detail = raw.get("detail", response.text)
            else:
                detail = response.text
            if isinstance(detail, list):
                detail = json.dumps(detail)
        except (json.JSONDecodeError, ValueError):
            detail = response.text or response.reason_phrase
        raise click.ClickException(f"API error {response.status_code}: {detail}")

    # --- JSON helpers -----------------------------------------------------

    def _as_dict(self, response: httpx.Response) -> dict[str, Any]:
        self._raise_for_status(response)
        if not response.content:
            return {}
        data = response.json()
        if not isinstance(data, dict):
            raise click.ClickException("Expected a JSON object from the API")
        return data

    def _as_list(self, response: httpx.Response) -> list[Any]:
        self._raise_for_status(response)
        data = response.json()
        if not isinstance(data, list):
            raise click.ClickException("Expected a JSON array from the API")
        return data

    def _as_any(self, response: httpx.Response) -> Any:
        self._raise_for_status(response)
        if not response.content:
            return None
        return response.json()

    # --- verbs ------------------------------------------------------------

    def get_dict(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self._as_dict(self._client.get(path, params=params or {}))

    def get_list(self, path: str, *, params: dict[str, Any] | None = None) -> list[Any]:
        return self._as_list(self._client.get(path, params=params or {}))

    def get_any(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self._as_any(self._client.get(path, params=params or {}))

    def post_dict(
        self,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._as_dict(
            self._client.post(path, params=params or {}, json=json_body)
        )

    def post_form_dict(self, path: str, *, data: dict[str, str]) -> dict[str, Any]:
        return self._as_dict(self._client.post(path, data=data))

    def post_any(
        self,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self._as_any(
            self._client.post(path, params=params or {}, json=json_body)
        )

    def patch_dict(
        self,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._as_dict(
            self._client.patch(path, params=params or {}, json=json_body)
        )

    def put_dict(
        self,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._as_dict(
            self._client.put(path, params=params or {}, json=json_body)
        )

    def delete_dict(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._as_dict(self._client.delete(path, params=params or {}))

    def delete_any(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self._as_any(self._client.delete(path, params=params or {}))

    # --- streaming --------------------------------------------------------

    def stream_sse(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Iterator[ServerSentEvent]:
        with self._client.stream(
            method, path, params=params or {}, json=json_body
        ) as response:
            self._raise_for_status(response)
            yield from EventSource(response).iter_sse()


class _BaseApi:
    """Common base for resource namespaces — holds the shared transport."""

    def __init__(self, transport: _Transport) -> None:
        self._t = transport
