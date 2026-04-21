"""Unit tests for prompt editor guidelines resolution."""

from app.services.prompt_editor.agent_prompt import (
    DEFAULT_EDITOR_GUIDELINES,
    get_effective_guidelines,
)


def test_get_effective_guidelines_returns_default_when_none() -> None:
    assert get_effective_guidelines(None) == DEFAULT_EDITOR_GUIDELINES


def test_get_effective_guidelines_returns_default_when_empty_string() -> None:
    assert get_effective_guidelines("") == DEFAULT_EDITOR_GUIDELINES
    assert get_effective_guidelines("   ") == DEFAULT_EDITOR_GUIDELINES


def test_get_effective_guidelines_returns_custom_when_set() -> None:
    custom = "  My custom rules.  "
    assert get_effective_guidelines(custom) == "My custom rules."


def test_default_guidelines_is_non_empty() -> None:
    assert len(DEFAULT_EDITOR_GUIDELINES) > 500
