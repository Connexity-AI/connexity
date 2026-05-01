"""Observed external calls (Retell call logs) attached to agents."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class CallsApi(_BaseApi):
    """Calls live under ``/agents/{agent_id}/calls`` and ``/calls/{call_id}``."""

    def list_for_agent(
        self, agent_id: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self._t.get_dict(f"agents/{agent_id}/calls", params=params)

    def refresh(self, agent_id: str) -> dict[str, Any]:
        return self._t.post_dict(f"agents/{agent_id}/calls/refresh")

    def get(self, call_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"calls/{call_id}")

    def mark_seen(self, call_id: str) -> dict[str, Any]:
        return self._t.post_dict(f"calls/{call_id}/seen")
