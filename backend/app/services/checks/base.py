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
from datetime import datetime
from enum import StrEnum

from pydantic import JsonValue
from sqlmodel import Session

from app.models.call import Call
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

    # Ids of the trace events it points at. At least one, unless the check judges the
    # call as a whole (``Check.whole_call``): then none, and ``key`` tells findings
    # apart.
    event_ids: tuple[str, ...]
    # The one thing that says what broke, for grouping into an issue.
    key: str | None = None
    # Small and structured. Never what a party said, a tool's arguments or its result.
    # A model's reason is its own paraphrase, told not to repeat names, numbers or
    # addresses (the spec check's LLM step).
    detail: dict[str, JsonValue] | None = None
    # The category key of the issue it joins, when it differs by finding (a spec rule's
    # category); the check's own otherwise.
    category: str | None = None
    # What its issue is named after, when the check's title does not say it (a spec
    # rule's text).
    subject: str | None = None
    # Never fails the call, whatever the check is set to (a spec rule not marked
    # critical).
    flags_only: bool = False
    # How this finding was found, when it differs from the check's kind (a spec rule
    # an LLM judged alone is a judge's finding in a classifier check).
    kind: CheckKind | None = None


@dataclass(frozen=True)
class Applies:
    """Whether a check judges one call, from what only the database knows."""

    # Why the call is skipped; None when the check judges it.
    skip: str | None = None
    # Findings on a call that started before this are retroactive: shown, counted for
    # nothing. None: the check's release.
    counts_from: datetime | None = None


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
    # Its findings may point at no event, when it judges the call as a whole; each
    # finding's key tells it apart, also from another at the same events.
    whole_call: bool = False
    # Reads the database to say whether it judges a call at all (the spec check needs
    # the agent's spec), given when the check was released. None: every call with what
    # ``needs`` asks for.
    applies: Callable[[Session, Call, datetime], Applies] | None = None


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


class AskFailed(Exception):
    """``ask`` failed after some of its requests were billed: their cost still counts
    for the daily budget."""

    def __init__(self, message: str, *, cost_usd: float) -> None:
        super().__init__(message)
        self.cost_usd = cost_usd


@dataclass(frozen=True, kw_only=True)
class ModelCheck(Check):
    """A classifier or a judge: ``ask`` once per call and version, then ``run``."""

    provider: ModelProvider
    # Pinned. A new model is a new version of the check.
    model: str
    # Called with the trace and what ``prepare`` read for the call (None without it).
    ask: Callable[[Trace, JsonValue], Awaitable[ModelReply]]
    # Reads what ``ask`` needs beyond the trace, before it is called (the spec check:
    # the rules and the call's inputs). Never what was said.
    prepare: Callable[[Session, Call], JsonValue] | None = None
    # An answer an earlier version stored stands for this one: a call is judged once,
    # and a new version reads the stored answer again instead of asking (the spec
    # check, Dmytro 2026-11-26: "New calls only"). ``run`` must read every earlier
    # version's answers.
    answers_carry_over: bool = False

    def __post_init__(self) -> None:
        if self.kind is CheckKind.CODE_BASED:
            msg = f"model check '{self.type}' must be a classifier or a judge"
            raise ValueError(msg)
