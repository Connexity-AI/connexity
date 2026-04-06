"""Generator tests are pure unit tests — no DB required."""

import json
from collections.abc import Generator

import pytest


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[None, None, None]:
    yield


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
        "status": "draft",
        "persona": {
            "type": f"test-persona-{i}",
            "description": f"A test persona for test case {i}",
            "instructions": f"Behave as persona {i} would.",
        },
        "initial_message": f"Hello, this is test message {i}.",
        "user_context": {"test_case_index": i, "test": True},
        "max_turns": 10,
        "expected_outcomes": {"success": True, "test_case_index": i},
        "expected_tool_calls": [
            {"tool": "test_tool", "expected_params": {"id": str(i)}}
        ],
    }
    for i in range(10)
]

MOCK_LLM_RESPONSE = json.dumps(MOCK_TEST_CASES_RAW)


@pytest.fixture()
def mock_llm_response() -> str:
    return MOCK_LLM_RESPONSE


@pytest.fixture()
def mock_test_cases_raw() -> list[dict]:
    return list(MOCK_TEST_CASES_RAW)
