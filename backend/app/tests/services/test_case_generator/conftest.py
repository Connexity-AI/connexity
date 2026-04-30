"""Shared fixtures and mocks for test_case_generator tests."""

import json

import pytest

MOCK_TEST_CASES_RAW: list[dict] = [
    {
        "name": f"Test TestCase {i}",
        "description": f"Test case description {i}",
        "difficulty": "normal" if i % 3 != 0 else "hard",
        "tags": [
            ["normal", "happy-path"],
            ["edge-case", "boundary"],
            ["red-team", "adversarial"],
        ][i % 3],
        "persona_context": (
            "[Persona type]\n"
            f"Test persona {i}\n"
            "[Description]\n"
            f"A realistic user for test case {i}. Their account id is {i}.\n"
            "[Behavioral instructions]\n"
            f"Behave as persona {i} would."
        ),
        "first_message": f"Hello, this is test message {i}.",
        "user_context": {"test_case_index": i, "test": True},
        "expected_outcomes": [f"Agent MUST handle test case {i} successfully"],
        "expected_tool_calls": [
            {
                "tool": "test_tool",
                "expected_params": {"id": str(i)},
                "mock_responses": [
                    {
                        "expected_params": {"id": str(i)},
                        "response": {"ok": True, "id": str(i)},
                    }
                ],
            }
        ],
    }
    for i in range(10)
]

MOCK_LLM_RESPONSE = json.dumps({"test_cases": MOCK_TEST_CASES_RAW})


@pytest.fixture()
def mock_llm_response() -> str:
    return MOCK_LLM_RESPONSE


@pytest.fixture()
def mock_test_cases_raw() -> list[dict]:
    return list(MOCK_TEST_CASES_RAW)
