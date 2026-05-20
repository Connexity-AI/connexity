"""Read-only API metadata: ``/config/*``."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class ConfigApi(_BaseApi):
    """``/config/*`` endpoints."""

    def show(self) -> dict[str, Any]:
        return self._t.get_dict("config/")

    def available_metrics(self) -> dict[str, Any]:
        return self._t.get_dict("config/available-metrics")

    def llm_models(self) -> dict[str, Any]:
        return self._t.get_dict("config/llm-models")

    def stt_models(self) -> dict[str, Any]:
        return self._t.get_dict("config/stt-models")

    def tts_models(self) -> dict[str, Any]:
        return self._t.get_dict("config/tts-models")

    def tts_voices(self, *, provider: str, model: str) -> dict[str, Any]:
        return self._t.get_dict(
            "config/tts-voices",
            params={"provider": provider, "model": model},
        )
