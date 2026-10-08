"""The call trace wire format: what a mapping sends and what the API returns.

A trace is not stored as a document. ``app.crud.trace`` stores each part once (call
columns, event rows, component rows) and assembles a trace from them on read. The
public description of this format is ``docs/traces/trace-schema.md``; keep the two in
step.
"""

from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    model_validator,
)

from app.models.enums import (
    CallChannel,
    CallDirection,
    CallEndReason,
    CallEventType,
    Speaker,
    ToolCallStatus,
    TraceSource,
)

TRACE_SCHEMA_VERSION = 1

EVENT_ID_MAX_LENGTH = 64


class _TraceModel(BaseModel):
    # Unknown fields are rejected so a mapping's typo is an error, not silently lost
    # data. Anything without a field belongs in ``extensions``.
    model_config = ConfigDict(extra="forbid")


class _TimedEvent(_TraceModel):
    id: str = Field(
        min_length=1,
        max_length=EVENT_ID_MAX_LENGTH,
        description="Unique within the trace; checks and comments point at it",
    )
    start_ms: int | None = Field(
        default=None, ge=0, description="Milliseconds from the start of the call"
    )
    span_id: str | None = Field(
        default=None,
        max_length=64,
        description="Copied from the source when it has one (OpenTelemetry span id)",
    )


class _SpanEvent(_TimedEvent):
    end_ms: int | None = Field(
        default=None, ge=0, description="Milliseconds from the start of the call"
    )

    @model_validator(mode="after")
    def end_follows_start(self) -> Self:
        if self.end_ms is None:
            return self
        if self.start_ms is None:
            msg = f"event '{self.id}' has end_ms but no start_ms"
            raise ValueError(msg)
        if self.end_ms < self.start_ms:
            msg = f"event '{self.id}' ends before it starts"
            raise ValueError(msg)
        return self


class UtteranceEvent(_SpanEvent):
    """Something a party said."""

    type: Literal[CallEventType.UTTERANCE] = CallEventType.UTTERANCE
    speaker: Speaker
    text: str = Field(description="What was said, as transcribed")
    interrupted: bool | None = Field(
        default=None, description="True if the other party cut it off"
    )


class ToolCallEvent(_SpanEvent):
    """One call from the agent to a tool, with its outcome in the same event."""

    type: Literal[CallEventType.TOOL_CALL] = CallEventType.TOOL_CALL
    name: str = Field(min_length=1, max_length=255)
    arguments: dict[str, JsonValue] | None = None
    status: ToolCallStatus | None = None
    result: JsonValue = Field(
        default=None, description="Parsed JSON if it parses, otherwise the raw string"
    )


class MarkerEvent(_TimedEvent):
    """Something that happened that is neither speech nor a tool call."""

    type: Literal[CallEventType.MARKER] = CallEventType.MARKER
    name: str = Field(min_length=1, max_length=255)
    detail: dict[str, JsonValue] | None = None


TraceEvent = Annotated[
    UtteranceEvent | ToolCallEvent | MarkerEvent, Field(discriminator="type")
]


class TraceComponent(_TraceModel):
    """One thing that served the call, with the version that was live."""

    kind: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    ref: str | None = Field(
        default=None, max_length=255, description="The provider's own identifier"
    )
    version: str | None = Field(default=None, max_length=255)
    fingerprint: str | None = Field(
        default=None,
        max_length=255,
        description="Hash of the content, for components with no version number",
    )


class TraceParties(_TraceModel):
    agent_number: str | None = Field(default=None, max_length=64)
    caller_number: str | None = Field(default=None, max_length=64)


class Trace(_TraceModel):
    """Connexity's record of one call, in a provider-neutral shape."""

    schema_version: Literal[1] = TRACE_SCHEMA_VERSION

    provider: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9_.-]*$",
        description="Free text, lower case; not a fixed list",
    )
    external_id: str = Field(
        min_length=1, max_length=255, description="The provider's own id for the call"
    )
    started_at: AwareDatetime

    source: TraceSource = TraceSource.PRODUCTION
    channel: CallChannel | None = None
    direction: CallDirection | None = None
    ended_at: AwareDatetime | None = None
    end_reason: CallEndReason | None = None
    end_reason_detail: str | None = Field(
        default=None, max_length=255, description="The provider's own wording"
    )
    trace_id: str | None = Field(default=None, max_length=64)
    parties: TraceParties | None = None
    recording_url: str | None = Field(default=None, max_length=2048)

    inputs: dict[str, JsonValue] | None = Field(
        default=None, description="Variables set before the call started"
    )
    components: list[TraceComponent] | None = None
    reports_tool_calls: bool | None = Field(
        default=None,
        description=(
            "True when the mapping includes every tool call the agent made, so a "
            "trace with no tool_call events means the agent made none"
        ),
    )
    events: list[TraceEvent]
    outputs: dict[str, JsonValue] | None = Field(
        default=None, description="What the provider concluded after the call"
    )
    extensions: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def empty_means_absent(self) -> Self:
        # "No components" and "no party numbers" have one representation each, so a
        # trace reads back from storage exactly as it was sent.
        if self.components is not None and not self.components:
            self.components = None
        if self.parties is not None and (
            self.parties.agent_number is None and self.parties.caller_number is None
        ):
            self.parties = None
        return self

    @model_validator(mode="after")
    def event_ids_are_unique(self) -> Self:
        seen: set[str] = set()
        for event in self.events:
            if event.id in seen:
                msg = f"event id '{event.id}' is used more than once"
                raise ValueError(msg)
            seen.add(event.id)
        return self

    @model_validator(mode="after")
    def call_ends_after_it_starts(self) -> Self:
        if self.ended_at is not None and self.ended_at < self.started_at:
            msg = "ended_at is before started_at"
            raise ValueError(msg)
        return self
