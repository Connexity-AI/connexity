"""Registry-level behaviour: which runtimes are advertised per platform."""

import pytest

from app.models.enums import Platform, RunMode, TextRuntimeKind
from app.services.eval_runtimes import (
    default_runtime_for_platform,
    get_runtime,
    runtimes_for_platform,
)
from app.services.eval_runtimes.text.connexity import ConnexityRuntime
from app.services.eval_runtimes.text.custom_endpoint import CustomEndpointRuntime
from app.services.eval_runtimes.text.retell import RetellRuntime


def test_get_runtime_returns_known_kinds() -> None:
    assert isinstance(
        get_runtime(RunMode.TEXT, TextRuntimeKind.CONNEXITY), ConnexityRuntime
    )
    assert isinstance(get_runtime(RunMode.TEXT, TextRuntimeKind.RETELL), RetellRuntime)
    assert isinstance(
        get_runtime(RunMode.TEXT, TextRuntimeKind.CUSTOM_ENDPOINT),
        CustomEndpointRuntime,
    )


def test_get_runtime_raises_for_unknown_kind() -> None:
    with pytest.raises(KeyError):
        get_runtime(RunMode.TEXT, "nonexistent")  # type: ignore[arg-type]


def test_runtimes_for_retell_platform() -> None:
    kinds = [e.KIND for e in runtimes_for_platform(Platform.RETELL)]
    assert TextRuntimeKind.CONNEXITY in kinds
    assert TextRuntimeKind.RETELL in kinds
    assert TextRuntimeKind.CUSTOM_ENDPOINT not in kinds


def test_runtimes_for_webhook_platform() -> None:
    kinds = [e.KIND for e in runtimes_for_platform(Platform.WEBHOOK)]
    assert TextRuntimeKind.CONNEXITY in kinds
    assert TextRuntimeKind.CUSTOM_ENDPOINT in kinds
    assert TextRuntimeKind.RETELL not in kinds


def test_runtimes_for_vapi_platform_includes_connexity_and_custom_endpoint() -> None:
    kinds = [e.KIND for e in runtimes_for_platform(Platform.VAPI)]
    assert kinds == [
        TextRuntimeKind.CONNEXITY,
        TextRuntimeKind.CUSTOM_ENDPOINT,
    ]


def test_runtimes_for_elevenlabs_platform_includes_connexity_and_custom_endpoint() -> (
    None
):
    kinds = [e.KIND for e in runtimes_for_platform(Platform.ELEVENLABS)]
    assert kinds == [
        TextRuntimeKind.CONNEXITY,
        TextRuntimeKind.CUSTOM_ENDPOINT,
    ]


def test_runtimes_for_none_platform_permits_connexity_and_custom_endpoint() -> None:
    # Legacy rows without a stored platform behave like a custom agent.
    kinds = [e.KIND for e in runtimes_for_platform(None)]
    assert TextRuntimeKind.CONNEXITY in kinds
    assert TextRuntimeKind.CUSTOM_ENDPOINT in kinds


def test_default_runtime_per_platform() -> None:
    assert default_runtime_for_platform(Platform.RETELL) == TextRuntimeKind.RETELL
    assert default_runtime_for_platform(Platform.WEBHOOK) == TextRuntimeKind.CONNEXITY
    assert default_runtime_for_platform(Platform.VAPI) == TextRuntimeKind.CONNEXITY
    assert default_runtime_for_platform(None) == TextRuntimeKind.CONNEXITY
