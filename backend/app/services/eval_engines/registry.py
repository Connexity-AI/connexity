"""Evaluation engine registry.

Single source of truth for which engines exist and which is the default for a
given agent platform. Adding an engine = create an :class:`EvalEngine` subclass
in its own module and append it here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.enums import EvaluationEngineKind, Platform
from app.services.eval_engines.base import EvalEngine
from app.services.eval_engines.connexity import ConnexityEngine
from app.services.eval_engines.custom_url import CustomUrlEngine
from app.services.eval_engines.retell import RetellEngine

if TYPE_CHECKING:
    pass


_ENGINES: dict[EvaluationEngineKind, EvalEngine] = {
    ConnexityEngine.KIND: ConnexityEngine(),
    RetellEngine.KIND: RetellEngine(),
    CustomUrlEngine.KIND: CustomUrlEngine(),
}


# Per-platform default engine. Connexity is always available as a fallback.
_DEFAULTS_BY_PLATFORM: dict[Platform | None, EvaluationEngineKind] = {
    None: EvaluationEngineKind.CONNEXITY,
    Platform.WEBHOOK: EvaluationEngineKind.CONNEXITY,
    Platform.RETELL: EvaluationEngineKind.RETELL,
    Platform.VAPI: EvaluationEngineKind.CONNEXITY,
    Platform.ELEVENLABS: EvaluationEngineKind.CONNEXITY,
}


def get_engine(kind: EvaluationEngineKind) -> EvalEngine:
    """Return the registered engine instance, or raise ``KeyError``."""
    return _ENGINES[kind]


def engines_for_platform(platform: Platform | None) -> list[EvalEngine]:
    """Return the engines (preserving stable order) available for ``platform``."""
    order = (
        EvaluationEngineKind.CONNEXITY,
        EvaluationEngineKind.RETELL,
        EvaluationEngineKind.CUSTOM_URL,
    )
    return [_ENGINES[k] for k in order if _ENGINES[k].supported_for_platform(platform)]


def default_engine_kind_for_platform(
    platform: Platform | None,
) -> EvaluationEngineKind:
    """Return the default engine kind for ``platform``."""
    return _DEFAULTS_BY_PLATFORM.get(platform, EvaluationEngineKind.CONNEXITY)
