"""Registry-level behaviour: which engines are advertised per platform."""

import pytest

from app.models.enums import EvaluationEngineKind, Platform
from app.services.eval_engines import (
    default_engine_kind_for_platform,
    engines_for_platform,
    get_engine,
)
from app.services.eval_engines.connexity import ConnexityEngine
from app.services.eval_engines.custom_url import CustomUrlEngine
from app.services.eval_engines.retell import RetellEngine


def test_get_engine_returns_known_kinds() -> None:
    assert isinstance(get_engine(EvaluationEngineKind.CONNEXITY), ConnexityEngine)
    assert isinstance(get_engine(EvaluationEngineKind.RETELL), RetellEngine)
    assert isinstance(get_engine(EvaluationEngineKind.CUSTOM_URL), CustomUrlEngine)


def test_get_engine_raises_for_unknown_kind() -> None:
    with pytest.raises(KeyError):
        get_engine("nonexistent")  # type: ignore[arg-type]


def test_engines_for_retell_platform() -> None:
    kinds = [e.KIND for e in engines_for_platform(Platform.RETELL)]
    assert EvaluationEngineKind.CONNEXITY in kinds
    assert EvaluationEngineKind.RETELL in kinds
    assert EvaluationEngineKind.CUSTOM_URL not in kinds


def test_engines_for_webhook_platform() -> None:
    kinds = [e.KIND for e in engines_for_platform(Platform.WEBHOOK)]
    assert EvaluationEngineKind.CONNEXITY in kinds
    assert EvaluationEngineKind.CUSTOM_URL in kinds
    assert EvaluationEngineKind.RETELL not in kinds


def test_engines_for_vapi_platform_is_connexity_only() -> None:
    kinds = [e.KIND for e in engines_for_platform(Platform.VAPI)]
    assert kinds == [EvaluationEngineKind.CONNEXITY]


def test_engines_for_elevenlabs_platform_is_connexity_only() -> None:
    kinds = [e.KIND for e in engines_for_platform(Platform.ELEVENLABS)]
    assert kinds == [EvaluationEngineKind.CONNEXITY]


def test_engines_for_none_platform_permits_connexity_and_custom_url() -> None:
    # Legacy rows without a stored platform behave like a custom agent.
    kinds = [e.KIND for e in engines_for_platform(None)]
    assert EvaluationEngineKind.CONNEXITY in kinds
    assert EvaluationEngineKind.CUSTOM_URL in kinds


def test_default_engine_per_platform() -> None:
    assert (
        default_engine_kind_for_platform(Platform.RETELL) == EvaluationEngineKind.RETELL
    )
    assert (
        default_engine_kind_for_platform(Platform.WEBHOOK)
        == EvaluationEngineKind.CONNEXITY
    )
    assert (
        default_engine_kind_for_platform(Platform.VAPI)
        == EvaluationEngineKind.CONNEXITY
    )
    assert default_engine_kind_for_platform(None) == EvaluationEngineKind.CONNEXITY
