"""Persona prompts for simulated caller persona (shared with backend user simulator logic)."""

from __future__ import annotations

from app.models.test_case import TestCase
from app.services.user_simulator import _build_system_prompt


def build_persona_system_prompt(test_case: TestCase) -> str:
    return _build_system_prompt(
        persona_context=test_case.persona_context,
        user_context=test_case.user_context,
        expected_outcomes=test_case.expected_outcomes,
    )
