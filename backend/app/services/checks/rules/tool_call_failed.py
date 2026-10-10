"""A tool call the trace reports as failed."""

from app.models.enums import CheckMode, ToolCallStatus
from app.models.trace import ToolCallEvent
from app.services.checks.base import CheckInput, Raised, RuleCheck

# "No result" is a different type: the tool was called and nothing came back.
_FAILED = (ToolCallStatus.ERROR, ToolCallStatus.TIMEOUT)


def _run(check_input: CheckInput) -> list[Raised]:
    return [
        Raised(
            event_ids=(event.id,),
            key=event.name,
            detail={"status": event.status.value},
        )
        for event in check_input.trace.events
        if isinstance(event, ToolCallEvent) and event.status in _FAILED
    ]


TOOL_CALL_FAILED = RuleCheck(
    type="tool_call_failed",
    version=1,
    title="Tool call failed",
    description="A tool the agent called returned an error or timed out.",
    default_mode=CheckMode.FAILS,
    run=_run,
)
