import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models.test_case import TestCaseCreate
from app.services.llm import LLMResponse
from app.services.test_case_generator.core import _parse_test_cases, generate_test_cases
from app.services.test_case_generator.schemas import GenerateRequest

from .conftest import MOCK_LLM_RESPONSE, MOCK_TEST_CASES_RAW


def _fake_llm_response(content: str = MOCK_LLM_RESPONSE) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="gpt-4o",
        usage={"prompt_tokens": 100, "completion_tokens": 500, "total_tokens": 600},
        latency_ms=1500,
    )


def test_parse_test_cases_valid_json(mock_llm_response: str) -> None:
    parsed = _parse_test_cases(mock_llm_response, expected_count=10)
    assert len(parsed) == 10
    assert all(isinstance(s, TestCaseCreate) for s in parsed)


def test_parse_test_cases_defaults_status_to_active() -> None:
    # The LLM no longer sees ``status``; the platform default (ACTIVE) applies,
    # and any stray ``status`` value the model emits is stripped.
    data = [
        {
            "name": "Test",
            "status": "draft",
            "tags": ["normal"],
            "persona_context": "A user. Be a user.",
            "first_message": "Hello",
        }
    ]
    parsed = _parse_test_cases(json.dumps(data), expected_count=1)
    assert parsed[0].status.value == "active"


def test_parse_test_cases_strips_markdown_fences() -> None:
    wrapped = f"```json\n{MOCK_LLM_RESPONSE}\n```"
    parsed = _parse_test_cases(wrapped, expected_count=10)
    assert len(parsed) == 10


def test_parse_test_cases_invalid_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_test_cases("not valid json at all", expected_count=1)


def test_parse_test_cases_not_array_raises() -> None:
    with pytest.raises(ValueError, match="not a JSON array"):
        _parse_test_cases('{"key": "value"}', expected_count=1)


def test_parse_test_cases_partial_results_logs_warning() -> None:
    # Only 1 test case but expecting 5
    data = [MOCK_TEST_CASES_RAW[0]]
    with patch("app.services.test_case_generator.core.logger") as mock_logger:
        parsed = _parse_test_cases(json.dumps(data), expected_count=5)
        assert len(parsed) == 1
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_generate_test_cases_calls_llm() -> None:
    request = GenerateRequest(
        agent_prompt="You are a test agent.",
        tools=[],
        count=10,
    )
    with patch(
        "app.services.test_case_generator.core.call_llm",
        new_callable=AsyncMock,
        return_value=_fake_llm_response(),
    ) as mock_call:
        created, model_used, latency_ms = await generate_test_cases(request)

    assert len(created) == 10
    assert latency_ms == 1500
    assert model_used == "gpt-4o"
    mock_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_test_cases_uses_config_default_model() -> None:
    request = GenerateRequest(
        agent_prompt="You are a test agent.",
        tools=[],
        count=10,
    )
    with (
        patch(
            "app.services.test_case_generator.core.call_llm",
            new_callable=AsyncMock,
            return_value=_fake_llm_response(),
        ),
        patch("app.services.test_case_generator.core.settings") as mock_settings,
    ):
        mock_settings.LLM_DEFAULT_MODEL = "gpt-4o"
        mock_settings.GENERATOR_MAX_TOKENS = 16_000
        _, model_used, _ = await generate_test_cases(request)

    assert model_used == "gpt-4o"


@pytest.mark.asyncio
async def test_generate_test_cases_respects_model_override() -> None:
    request = GenerateRequest(
        agent_prompt="You are a test agent.",
        tools=[],
        count=10,
        model="gpt-4o-mini",
    )
    resp = _fake_llm_response()
    resp.model = "gpt-4o-mini"
    with (
        patch(
            "app.services.test_case_generator.core.call_llm",
            new_callable=AsyncMock,
            return_value=resp,
        ) as mock_call,
        patch("app.services.test_case_generator.core.settings") as mock_settings,
    ):
        mock_settings.LLM_DEFAULT_MODEL = "gpt-4o"
        mock_settings.GENERATOR_MAX_TOKENS = 16_000
        _, model_used, _ = await generate_test_cases(request)

    assert model_used == "gpt-4o-mini"
    # Verify the config passed to call_llm has the override model
    call_config = mock_call.await_args.kwargs.get("config") or mock_call.await_args[1]
    assert call_config.model == "gpt-4o-mini"
