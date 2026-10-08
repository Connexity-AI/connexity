"""What a trace can support, derived from what it contains.

A check declares the capabilities it needs. When a trace lacks one, the check is
skipped for that trace and says so; it never passes silently. The definitions here are
the ones published in ``docs/traces/trace-schema.md``.
"""

from app.models.enums import TraceCapability
from app.models.trace import ToolCallEvent, Trace


def derive_capabilities(trace: Trace) -> list[TraceCapability]:
    """Return the capabilities of ``trace``, in a stable order."""
    tool_calls = [event for event in trace.events if isinstance(event, ToolCallEvent)]
    capabilities: list[TraceCapability] = []

    # No tool_call events only means "the agent called nothing" when the mapping says
    # it reports tool calls. Otherwise the provider may simply not expose them.
    has_tool_calls = bool(tool_calls) or trace.reports_tool_calls is True
    if has_tool_calls:
        capabilities.append(TraceCapability.TOOL_CALLS)
        if all(event.status is not None for event in tool_calls):
            capabilities.append(TraceCapability.TOOL_RESULTS)

    if trace.events and all(event.start_ms is not None for event in trace.events):
        capabilities.append(TraceCapability.TIMING)

    if trace.inputs is not None:
        capabilities.append(TraceCapability.INPUTS)

    if any(
        component.version is not None or component.fingerprint is not None
        for component in trace.components or []
    ):
        capabilities.append(TraceCapability.COMPONENTS)

    if trace.recording_url is not None:
        capabilities.append(TraceCapability.RECORDING)

    if trace.outputs is not None:
        capabilities.append(TraceCapability.OUTPUTS)

    return capabilities
