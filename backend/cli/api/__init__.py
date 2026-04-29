"""Resource-namespaced HTTP client for the Connexity Evals REST API.

Usage:
    >>> with ApiClient(base_url=..., token=...) as client:
    ...     run = client.runs.get(run_id)
    ...     agents = client.agents.list()
"""

from __future__ import annotations

from typing import Self

from cli.api._base import (
    API_PREFIX,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    _Transport,
)
from cli.api.agents import AgentsApi
from cli.api.auth import AuthApi
from cli.api.calls import CallsApi
from cli.api.config import ConfigApi
from cli.api.custom_metrics import CustomMetricsApi
from cli.api.environments import EnvironmentsApi
from cli.api.eval_configs import EvalConfigsApi
from cli.api.health import HealthApi
from cli.api.integrations import IntegrationsApi
from cli.api.prompt_editor import PromptEditorApi
from cli.api.runs import RunsApi
from cli.api.test_case_results import TestCaseResultsApi
from cli.api.test_cases import TestCasesApi
from cli.api.users import UsersApi

__all__ = [
    "API_PREFIX",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "ApiClient",
]


class ApiClient:
    """Composed HTTP client. Each resource is exposed as a typed attribute."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._t = _Transport(base_url, token, timeout=timeout)
        self.auth = AuthApi(self._t)
        self.users = UsersApi(self._t)
        self.agents = AgentsApi(self._t)
        self.test_cases = TestCasesApi(self._t)
        self.test_case_results = TestCaseResultsApi(self._t)
        self.eval_configs = EvalConfigsApi(self._t)
        self.runs = RunsApi(self._t)
        self.custom_metrics = CustomMetricsApi(self._t)
        self.prompt_editor = PromptEditorApi(self._t)
        self.integrations = IntegrationsApi(self._t)
        self.environments = EnvironmentsApi(self._t)
        self.calls = CallsApi(self._t)
        self.config = ConfigApi(self._t)
        self.health = HealthApi(self._t)

    def close(self) -> None:
        self._t.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
