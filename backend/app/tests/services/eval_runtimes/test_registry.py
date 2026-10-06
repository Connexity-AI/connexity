"""Registry-level behaviour: which runtimes are advertised per platform."""

import pytest

from app.models.enums import Platform, RunMode, TextRuntimeKind
from app.services.eval_runtimes import (
    default_runtime_for_platform,
    get_runtime,
    runtimes_for_platform,
)
from app.services.eval_runtimes.text.custom_endpoint import CustomEndpointRuntime
from app.services.eval_runtimes.text.retell import RetellRuntime


def test_get_runtime_returns_known_kinds() -> None:
    assert isinstance(get_runtime(RunMode.TEXT, TextRuntimeKind.RETELL), RetellRuntime)
    assert isinstance(
        get_runtime(RunMode.TEXT, TextRuntimeKind.CUSTOM_ENDPOINT),
        CustomEndpointRuntime,
    )


def test_get_runtime_raises_for_unknown_kind() -> None:
    with pytest.raises(KeyError):
        get_runtime(RunMode.TEXT, "nonexistent")  # type: ignore[arg-type]


def test_get_runtime_no_longer_knows_the_in_house_simulator() -> None:
    with pytest.raises(KeyError):
        get_runtime(RunMode.TEXT, "connexity")  # type: ignore[arg-type]


def test_runtimes_for_retell_platform() -> None:
    kinds = [e.KIND for e in runtimes_for_platform(Platform.RETELL)]
    assert kinds == [TextRuntimeKind.RETELL]


@pytest.mark.parametrize(
    "platform", [Platform.WEBHOOK, Platform.VAPI, Platform.ELEVENLABS, None]
)
def test_runtimes_for_platforms_without_a_connector(platform: Platform | None) -> None:
    # No first-party connector: the team's own endpoint is the only engine.
    kinds = [e.KIND for e in runtimes_for_platform(platform)]
    assert kinds == [TextRuntimeKind.CUSTOM_ENDPOINT]


def test_default_runtime_per_platform() -> None:
    assert default_runtime_for_platform(Platform.RETELL) == TextRuntimeKind.RETELL
    for platform in (Platform.WEBHOOK, Platform.VAPI, Platform.ELEVENLABS, None):
        assert default_runtime_for_platform(platform) == TextRuntimeKind.CUSTOM_ENDPOINT
