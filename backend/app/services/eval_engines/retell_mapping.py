from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.models.enums import TurnRole
from app.models.schemas import ConversationTurn

if TYPE_CHECKING:
    from app.models.test_case import TestCase


def build_retell_user_prompt(
    test_case: TestCase, *, max_turns: int | None = None
) -> str:
    sections: list[str] = []
    turn_limit = _retell_turn_limit(max_turns)

    simulation_rules = [
        "Play the simulated user only.",
        "Act like a real caller with this scenario, not like an evaluator.",
        "Do not try to force every expected outcome; Retell will evaluate those separately.",
        "Do not repeat the same message, concern, or question.",
        "Answer the agent's questions with concrete new information from the scenario.",
        "If the agent asks a question that is not covered by the scenario, give a short plausible answer and move on.",
        "End the conversation as soon as the agent gives a clear next step or safety instruction.",
        "If the conversation is not progressing, give one final useful detail and then end the conversation.",
        f"Keep the simulation under {turn_limit} total turns.",
    ]
    sections.append("Simulation rules:\n" + "\n".join(f"- {rule}" for rule in simulation_rules))

    if test_case.name:
        sections.append(f"Test case: {test_case.name}")
    if test_case.description:
        sections.append(f"Scenario: {test_case.description}")
    if test_case.persona_context:
        sections.append(f"Persona: {test_case.persona_context}")
    if test_case.first_message:
        sections.append(f"Start the conversation with: {test_case.first_message}")
    if test_case.user_context:
        sections.append(
            "User context: "
            f"{json.dumps(test_case.user_context, sort_keys=True, default=str)}"
        )
    return "\n\n".join(sections)


def _retell_turn_limit(max_turns: int | None) -> int:
    if max_turns is None:
        return 8
    return max(4, min(max_turns, 8))


def build_retell_metrics(test_case: TestCase) -> list[str]:
    if test_case.expected_outcomes:
        return [outcome for outcome in test_case.expected_outcomes if outcome]
    if test_case.evaluation_criteria_override:
        return [test_case.evaluation_criteria_override]
    return ["Task completion"]


def build_retell_dynamic_variables(test_case: TestCase) -> dict[str, str]:
    return {
        "test_case_id": str(test_case.id),
        "test_case_name": test_case.name or "",
        "persona_context": test_case.persona_context or "",
        "first_message": test_case.first_message or "",
    }


def map_retell_transcript_snapshot(
    transcript_snapshot: dict[str, Any] | None,
) -> list[ConversationTurn]:
    if not transcript_snapshot:
        return []

    raw_items = _extract_transcript_items(transcript_snapshot)
    turns: list[ConversationTurn] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        role = _map_retell_role(item.get("role") or item.get("speaker"))
        if role is None:
            continue
        content = item.get("content") or item.get("message") or item.get("text")
        if not isinstance(content, str) or not content:
            continue
        turns.append(
            ConversationTurn(
                index=len(turns),
                role=role,
                content=content,
                timestamp=_map_retell_timestamp(item.get("timestamp")),
            )
        )
    return turns


def _extract_transcript_items(transcript_snapshot: dict[str, Any]) -> list[Any]:
    for key in ("messages", "transcript", "turns", "conversation"):
        value = transcript_snapshot.get(key)
        if isinstance(value, list):
            return value
    return []


def _map_retell_role(raw_role: object) -> TurnRole | None:
    role = str(raw_role or "").lower()
    if role in {"agent", "assistant", "bot"}:
        return TurnRole.ASSISTANT
    if role == "user":
        return TurnRole.USER
    return None


def _map_retell_timestamp(raw_timestamp: object) -> datetime:
    if isinstance(raw_timestamp, int | float):
        timestamp_seconds = raw_timestamp / 1000 if raw_timestamp > 10_000_000_000 else raw_timestamp
        return datetime.fromtimestamp(timestamp_seconds, tz=UTC)
    return datetime.fromtimestamp(time.time(), tz=UTC)
