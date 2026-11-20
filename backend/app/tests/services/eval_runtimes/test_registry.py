"""Registry-level behaviour: which runtimes exist."""

import pytest

from app.models.enums import RunMode, TextRuntimeKind
from app.services.eval_runtimes import get_runtime
from app.services.eval_runtimes.text.retell import RetellRuntime


def test_get_runtime_returns_known_kinds() -> None:
    assert isinstance(get_runtime(RunMode.TEXT, TextRuntimeKind.RETELL), RetellRuntime)


def test_get_runtime_raises_for_unknown_kind() -> None:
    with pytest.raises(KeyError):
        get_runtime(RunMode.TEXT, "nonexistent")  # type: ignore[arg-type]


def test_get_runtime_does_not_know_a_custom_endpoint() -> None:
    with pytest.raises(KeyError):
        get_runtime(RunMode.TEXT, "custom_endpoint")  # type: ignore[arg-type]
