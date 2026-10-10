"""What a rule check and a fact are.

Both are pure: they read the trace and the executions they are given, and nothing else.
No database, no network, no model. That is what lets a check run on every call as it
arrives and be tested with an invented trace.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from pydantic import JsonValue

from app.models.enums import CheckKind, CheckMode
from app.models.execution import Execution
from app.models.trace import Trace


@dataclass(frozen=True)
class Fact:
    """A value derived from the trace, attached to the events it was derived from."""

    event_ids: tuple[str, ...]
    value: JsonValue


@dataclass(frozen=True)
class FactSource:
    name: str
    # Raised by hand whenever ``derive`` would answer differently for the same call.
    version: int
    derive: Callable[[Trace, list[Execution]], list[Fact]]


@dataclass(frozen=True)
class CheckInput:
    trace: Trace
    executions: list[Execution]
    # Only the facts the check asked for, by the name of their source.
    facts: Mapping[str, list[Fact]] = field(default_factory=dict)


@dataclass(frozen=True)
class Raised:
    """A finding as a check reports it, before it is stored."""

    # Ids of the trace events it points at. At least one.
    event_ids: tuple[str, ...]
    # The one thing that says what broke, for grouping into an issue.
    key: str | None = None
    # Small and structured. Never what a party said, a tool's arguments or its result.
    detail: dict[str, JsonValue] | None = None


@dataclass(frozen=True)
class RuleCheck:
    type: str
    # Raised by hand whenever ``run`` would answer differently for the same call.
    version: int
    title: str
    description: str
    default_mode: CheckMode
    run: Callable[[CheckInput], list[Raised]]
    facts: tuple[str, ...] = ()
    kind: CheckKind = CheckKind.RULE
