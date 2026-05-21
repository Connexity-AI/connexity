"""Evaluation runtime package — pluggable strategies for driving an eval run.

See ``docs/evals/runtimes.md`` for how to add a new runtime.
"""

from app.services.eval_runtimes.base import (
    EvalRuntime,
    RuntimeRunArgs,
    RuntimeTestResult,
)
from app.services.eval_runtimes.registry import (
    default_runtime_for_platform,
    get_runtime,
    runtimes_for_platform,
)
from app.services.eval_runtimes.types import (
    AgentSnapshot,
    RunSnapshot,
    TestCaseRunResult,
)

__all__ = [
    "AgentSnapshot",
    "EvalRuntime",
    "RunSnapshot",
    "RuntimeRunArgs",
    "RuntimeTestResult",
    "TestCaseRunResult",
    "default_runtime_for_platform",
    "get_runtime",
    "runtimes_for_platform",
]
