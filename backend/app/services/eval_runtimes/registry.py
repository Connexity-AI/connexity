"""Evaluation runtime registry.

Single source of truth for which runtimes exist and which is the default for a
given agent platform. Adding a runtime = create an :class:`EvalRuntime` subclass
in its own module and append it here.
"""

from app.models.enums import Platform, RunMode, TextRuntimeKind
from app.services.eval_runtimes.base import EvalRuntime
from app.services.eval_runtimes.text.custom_endpoint import CustomEndpointRuntime
from app.services.eval_runtimes.text.retell import RetellRuntime

_TEXT_RUNTIMES: dict[TextRuntimeKind, EvalRuntime] = {
    RetellRuntime.KIND: RetellRuntime(),
    CustomEndpointRuntime.KIND: CustomEndpointRuntime(),
}


# Per-platform default runtime. Platforms without a first-party connector fall
# back to the custom endpoint runtime (the team's own deployed agent).
_TEXT_DEFAULTS_BY_PLATFORM: dict[Platform | None, TextRuntimeKind] = {
    Platform.RETELL: TextRuntimeKind.RETELL,
}


def get_runtime(mode: RunMode, kind: TextRuntimeKind) -> EvalRuntime:
    """Return the registered runtime instance, or raise ``KeyError``."""
    if mode == RunMode.TEXT:
        return _TEXT_RUNTIMES[kind]
    msg = f"No runtimes registered for mode {mode.value}"
    raise KeyError(msg)


def runtimes_for_platform(platform: Platform | None) -> list[EvalRuntime]:
    """Return text runtimes available for ``platform`` in stable display order."""
    order = (
        TextRuntimeKind.RETELL,
        TextRuntimeKind.CUSTOM_ENDPOINT,
    )
    return [
        _TEXT_RUNTIMES[k]
        for k in order
        if _TEXT_RUNTIMES[k].supported_for_platform(platform)
    ]


def default_runtime_for_platform(
    platform: Platform | None,
) -> TextRuntimeKind:
    """Return the default text runtime kind for ``platform``."""
    return _TEXT_DEFAULTS_BY_PLATFORM.get(platform, TextRuntimeKind.CUSTOM_ENDPOINT)
