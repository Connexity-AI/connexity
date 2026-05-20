from datetime import UTC, datetime

from app.models.agent_contract import ChatMessage
from app.models.enums import TurnRole
from app.models.schemas import ToolCall, ToolCallFunction
from app.services.voice_transcript import (
    conversation_turns_from_job_transcript,
    map_chat_messages_to_conversation_transcript,
)


def test_map_chat_messages_simple_user_assistant() -> None:
    base = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)
    messages = [
        ChatMessage(role=TurnRole.USER, content="I need help."),
        ChatMessage(role=TurnRole.ASSISTANT, content="Sure."),
    ]

    transcript = map_chat_messages_to_conversation_transcript(
        messages, base_timestamp=base
    )

    assert len(transcript) == 2
    assert transcript[0].index == 0
    assert transcript[0].role == TurnRole.USER
    assert transcript[0].content == "I need help."
    assert transcript[0].timestamp == base
    assert transcript[1].index == 1
    assert transcript[1].role == TurnRole.ASSISTANT


def test_map_chat_messages_tool_flow() -> None:
    messages = [
        ChatMessage(
            role=TurnRole.ASSISTANT,
            content="Checking…",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    function=ToolCallFunction(
                        name="lookup_order",
                        arguments='{"order_id":"123"}',
                    ),
                ),
            ],
        ),
        ChatMessage(
            role=TurnRole.TOOL,
            tool_call_id="call_1",
            name="lookup_order",
            content='{"status":"shipped"}',
        ),
        ChatMessage(role=TurnRole.ASSISTANT, content="Your order shipped."),
    ]

    transcript = map_chat_messages_to_conversation_transcript(messages)

    assert len(transcript) == 3
    assert transcript[0].tool_calls is not None
    assert transcript[0].tool_calls[0].function.name == "lookup_order"
    assert transcript[1].role == TurnRole.TOOL
    assert transcript[1].tool_call_id == "call_1"
    assert transcript[1].content == '{"status":"shipped"}'
    assert transcript[2].content == "Your order shipped."


def test_conversation_turns_from_job_transcript_round_trip() -> None:
    messages = [ChatMessage(role=TurnRole.USER, content="Hi")]
    turns = map_chat_messages_to_conversation_transcript(messages)
    raw = [t.model_dump(mode="json") for t in turns]

    restored = conversation_turns_from_job_transcript(raw)

    assert len(restored) == 1
    assert restored[0].role == TurnRole.USER
    assert restored[0].content == "Hi"
