"""Shared fixtures for CLI tests.

We isolate the CLI from the real FastAPI app by mocking httpx via ``respx``.
Tests assert on (a) the HTTP request the CLI built and (b) the parsed
response surfaced to stdout. Real backend integration is covered by
``app/tests/`` separately.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import respx
from click.testing import CliRunner

API_BASE = "http://api.test.local"
API_ROOT = f"{API_BASE}/api/v1"
TOKEN = "test-token-abc"


@pytest.fixture
def runner() -> CliRunner:
    """Click test runner that mixes stderr into the output buffer for assertions."""
    return CliRunner(mix_stderr=False)


@pytest.fixture
def api_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Point the CLI at the mocked API and isolate credential storage."""
    monkeypatch.setenv("CONNEXITY_CLI_API_URL", API_BASE)
    monkeypatch.setenv("CONNEXITY_CLI_API_TOKEN", TOKEN)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    yield


@pytest.fixture
def respx_mock_clean() -> Iterator[respx.MockRouter]:
    """A respx router that asserts every registered route is consumed."""
    with respx.mock(base_url=API_ROOT, assert_all_called=True) as router:
        yield router


@pytest.fixture
def respx_mock() -> Iterator[respx.MockRouter]:
    """Lenient respx router (does not require every mock to be hit)."""
    with respx.mock(base_url=API_ROOT, assert_all_called=False) as router:
        yield router
