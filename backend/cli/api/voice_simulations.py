"""Voice simulation jobs (phone-call eval lifecycle)."""

from __future__ import annotations

from typing import Any

from cli.api._base import _BaseApi


class VoiceSimulationsApi(_BaseApi):
    """``/voice-simulations/*`` endpoints."""

    def list_jobs_for_run(
        self, run_id: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self._t.get_dict(f"voice-simulations/runs/{run_id}/jobs", params=params)

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self._t.get_dict(f"voice-simulations/jobs/{job_id}")
