"""Prompt editor sessions, messages, presets, and SSE chat streaming."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from httpx_sse import ServerSentEvent

from cli.api._base import _BaseApi


class PromptEditorApi(_BaseApi):
    """``/prompt-editor/*`` endpoints."""

    # --- sessions ---------------------------------------------------------

    def list_sessions(self, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._t.get_dict("prompt-editor/sessions/", params=params)

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"prompt-editor/sessions/{session_id}")

    def create_session(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_dict("prompt-editor/sessions/", json_body=body)

    def update_session(self, session_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._t.patch_dict(
            f"prompt-editor/sessions/{session_id}", json_body=body
        )

    def update_session_base_prompt(
        self, session_id: str, *, base_prompt: str
    ) -> dict[str, Any]:
        return self._t.patch_dict(
            f"prompt-editor/sessions/{session_id}/base-prompt",
            json_body={"base_prompt": base_prompt},
        )

    def delete_session(self, session_id: str) -> dict[str, Any]:
        return self._t.delete_dict(f"prompt-editor/sessions/{session_id}")

    # --- messages ---------------------------------------------------------

    def list_messages(
        self, session_id: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self._t.get_dict(
            f"prompt-editor/sessions/{session_id}/messages", params=params
        )

    def chat_stream(
        self, session_id: str, body: dict[str, Any]
    ) -> Iterator[ServerSentEvent]:
        yield from self._t.stream_sse(
            "POST",
            f"prompt-editor/sessions/{session_id}/messages",
            json_body=body,
        )

    # --- presets ----------------------------------------------------------

    def get_presets(self, *, params: dict[str, Any] | None = None) -> list[Any]:
        return self._t.get_list("prompt-editor/presets", params=params)
