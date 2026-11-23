"""Runtime package: pluggable strategies for driving one simulated call on the
agent's own engine."""

from app.services.eval_runtimes.base import (
    EvalRuntime,
    RuntimeRunArgs,
)
from app.services.eval_runtimes.registry import (
    get_runtime,
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
    "TestCaseRunResult",
    "get_runtime",
]
