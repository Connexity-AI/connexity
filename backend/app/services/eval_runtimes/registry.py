"""Evaluation runtime registry.

Single source of truth for which runtimes exist. Adding a runtime = create an
:class:`EvalRuntime` subclass in its own module and append it here.
"""

from app.models.enums import RunMode, TextRuntimeKind
from app.services.eval_runtimes.base import EvalRuntime
from app.services.eval_runtimes.text.retell import RetellRuntime

_TEXT_RUNTIMES: dict[TextRuntimeKind, EvalRuntime] = {
    RetellRuntime.KIND: RetellRuntime(),
}


def get_runtime(mode: RunMode, kind: TextRuntimeKind) -> EvalRuntime:
    """Return the registered runtime instance, or raise ``KeyError``."""
    if mode == RunMode.TEXT:
        return _TEXT_RUNTIMES[kind]
    msg = f"No runtimes registered for mode {mode.value}"
    raise KeyError(msg)
