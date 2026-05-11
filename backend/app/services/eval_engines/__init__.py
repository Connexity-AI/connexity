"""Evaluation engine package — pluggable strategies for driving an eval run.

See ``docs/eval-engines.md`` for how to add a new engine.
"""

from app.services.eval_engines.base import (
    EngineRunArgs,
    EngineTestResult,
    EvalEngine,
)
from app.services.eval_engines.registry import (
    default_engine_kind_for_platform,
    engines_for_platform,
    get_engine,
)

__all__ = [
    "EngineRunArgs",
    "EngineTestResult",
    "EvalEngine",
    "default_engine_kind_for_platform",
    "engines_for_platform",
    "get_engine",
]
