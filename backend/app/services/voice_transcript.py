"""Map user-submitted OpenAI-format messages to Connexity conversation turns."""

from datetime import UTC, datetime

from app.models.agent_contract import ChatMessage
from app.models.schemas import ConversationTurn


def map_chat_messages_to_conversation_transcript(
    messages: list[ChatMessage],
    *,
    base_timestamp: datetime | None = None,
) -> list[ConversationTurn]:
    """Convert submitted agent-side messages into judge-ready transcript turns.

    Each :class:`ChatMessage` becomes one :class:`ConversationTurn` in order,
    preserving tool calls and tool-result turns as separate entries (same shape
    as text runtimes' wire-message append path).
    """
    timestamp = base_timestamp or datetime.now(UTC)
    transcript: list[ConversationTurn] = []
    for message in messages:
        transcript.append(
            ConversationTurn(
                index=len(transcript),
                role=message.role,
                content=message.content,
                tool_calls=message.tool_calls,
                tool_call_id=message.tool_call_id,
                timestamp=timestamp,
            )
        )
    return transcript


def conversation_turns_from_job_transcript(
    raw: list[dict[str, object]] | None,
) -> list[ConversationTurn]:
    if not raw:
        msg = "Voice job has no normalized transcript"
        raise ValueError(msg)
    return [ConversationTurn.model_validate(item) for item in raw]
