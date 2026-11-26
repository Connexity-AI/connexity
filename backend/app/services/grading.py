"""Whether a call qualifies to be graded: the agent said enough to judge.

A call where the agent spoke fewer than ``GRADING_MIN_AGENT_WORDS`` words is not graded
(Decided, Dmytro 2026-11-26): it is never judged against the spec, and when nothing was
found on it, it is "not graded" instead of clean and counts in no score, so it cannot
lift the score by looking like a call that passed. A finding a code check made on it
still counts, because that failure is real. The floor counts the agent's words, not
seconds, whatever the kind of call. See `plans/2026-11-26-call-must-qualify.md`.
"""

from collections.abc import Iterable

from app.models.enums import Speaker
from app.models.trace import TraceEvent, UtteranceEvent

GRADING_MIN_AGENT_WORDS = 10
NOT_GRADED_REASON = f"the agent spoke fewer than {GRADING_MIN_AGENT_WORDS} words"


def agent_word_count(events: Iterable[TraceEvent]) -> int:
    """The words in the agent's turns, split on whitespace. Caller and other speakers
    do not count. The migration that filled this in for stored calls counts the same
    way (`0055_call_agent_words`)."""
    return sum(
        len(event.text.split())
        for event in events
        if isinstance(event, UtteranceEvent) and event.speaker == Speaker.AGENT
    )


def is_graded(agent_words: int | None) -> bool:
    """False only when the count is known and under the floor. A call with no trace
    has no count, and no check runs on it either."""
    return agent_words is None or agent_words >= GRADING_MIN_AGENT_WORDS
