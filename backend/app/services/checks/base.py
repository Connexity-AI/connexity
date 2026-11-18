"""What a check and a fact are.

Every check, whatever decides it, has a pure ``run``: it reads the trace, the
executions and, for a model check, the model's stored answer, and nothing else. No
database, no network. That is what lets a check run on every call as it arrives, be
run again for free, and be tested with an invented trace.

The three kinds (`CheckKind`):

- **Code-based** (`Check`): ``run`` is all of it.
- **Classifier** and **judge** (`ModelCheck`): ``ask`` puts the check's questions to a
  model, once per call and check version, and its answer is stored
  (`ModelAnswer`). ``run`` then turns the answer and the trace into findings. A
  classifier asks typed questions (Jev); a judge asks a language model.

The kind of check does not change severity: that comes from ``default_mode``, the
issue type's default (Dmytro, 2026-11-17).
"""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import JsonValue

from app.models.enums import CheckKind, CheckMode, TraceCapability
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
    # A model check's stored answer for this call; None for a code-based check.
    answer: JsonValue = None


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
class Check:
    type: str
    # Raised by hand whenever ``run`` (or a model check's ``ask``) would answer
    # differently for the same call. A new version of a model check asks again.
    version: int
    title: str
    description: str
    default_mode: CheckMode
    # The key of the category its issues belong to (`app/models/category.py`).
    category: str
    run: Callable[[CheckInput], list[Raised]]
    facts: tuple[str, ...] = ()
    # What a trace must have for the check to say anything. On a call without it the
    # check is skipped, which is recorded and is not a pass.
    needs: tuple[TraceCapability, ...] = ()
    kind: CheckKind = CheckKind.CODE_BASED
    # What each key of a finding's ``detail`` means, for the assistant (``get_issue``).
    detail_fields: Mapping[str, str] = field(default_factory=dict)


class ModelProvider(StrEnum):
    TYPESAFE = "typesafe"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass(frozen=True)
class ModelReply:
    """What ``ask`` returns: the answer to store, and what asking cost."""

    # Labels and verdicts keyed by event ids. Never what a party said.
    answer: JsonValue
    # The versioned model that answered.
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    requests: int = 1


@dataclass(frozen=True, kw_only=True)
class ModelCheck(Check):
    """A classifier or a judge: ``ask`` once per call and version, then ``run``."""

    provider: ModelProvider
    # Pinned. A new model is a new version of the check.
    model: str
    ask: Callable[[Trace], Awaitable[ModelReply]]

    def __post_init__(self) -> None:
        if self.kind is CheckKind.CODE_BASED:
            msg = f"model check '{self.type}' must be a classifier or a judge"
            raise ValueError(msg)
