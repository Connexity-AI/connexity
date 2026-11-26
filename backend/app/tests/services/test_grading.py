"""Whether a call is graded: the agent's words against the floor."""

from app.models.enums import Speaker
from app.models.trace import ToolCallEvent, UtteranceEvent
from app.services.grading import (
    GRADING_MIN_AGENT_WORDS,
    agent_word_count,
    is_graded,
)


def _say(speaker: Speaker, text: str, n: int) -> UtteranceEvent:
    return UtteranceEvent(
        id=f"e{n}",
        type="utterance",
        start_ms=n,
        end_ms=n + 1,
        speaker=speaker,
        text=text,
    )


def test_only_the_agents_words_count() -> None:
    events = [
        _say(Speaker.AGENT, "  Hi,\nthis is   Sam ", 0),
        _say(Speaker.CALLER, "one two three four five six seven eight", 1),
        _say(Speaker.OTHER, "transferring you now", 2),
        ToolCallEvent(
            id="t1", type="tool_call", start_ms=3, end_ms=4, name="lookup", status="ok"
        ),
        _say(Speaker.AGENT, "", 5),
    ]
    assert agent_word_count(events) == 4


def test_the_floor_is_ten_words_and_no_trace_is_not_short() -> None:
    assert GRADING_MIN_AGENT_WORDS == 10
    assert is_graded(10)
    assert not is_graded(9)
    assert not is_graded(0)
    assert is_graded(None)
