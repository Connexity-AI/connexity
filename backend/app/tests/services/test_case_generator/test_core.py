import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models.test_case import TestCaseCreate
from app.services.llm import LLMResponse
from app.services.test_case_generator.batch.core import (
    GenerationValidationError,
    _parse_test_cases,
    generate_test_cases,
)
from app.services.test_case_generator.batch.schemas import (
    GenerateRequest,
    ToolDefinition,
)

from .conftest import MOCK_LLM_RESPONSE, MOCK_TEST_CASES_RAW


def _fake_llm_response(content: str = MOCK_LLM_RESPONSE) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="gpt-4o",
        usage={"prompt_tokens": 100, "completion_tokens": 500, "total_tokens": 600},
        latency_ms=1500,
    )


def _test_tool() -> ToolDefinition:
    return ToolDefinition(
        name="test_tool",
        parameters={
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    )


def _no_param_tool() -> ToolDefinition:
    return ToolDefinition(
        name="test_tool",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
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
            "persona_context": (
                "[Persona type]\nCustomer\n"
                "[Description]\nA user testing defaults.\n"
                "[Behavioral instructions]\nBe concise."
            ),
            "first_message": "Hello",
        }
    ]
    parsed = _parse_test_cases(json.dumps({"test_cases": data}), expected_count=1)
    assert parsed[0].status.value == "active"


def test_parse_test_cases_strips_markdown_fences() -> None:
    wrapped = f"```json\n{MOCK_LLM_RESPONSE}\n```"
    parsed = _parse_test_cases(wrapped, expected_count=10)
    assert len(parsed) == 10


def test_parse_test_cases_invalid_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_test_cases("not valid json at all", expected_count=1)


def test_parse_test_cases_not_array_raises() -> None:
    with pytest.raises(ValueError, match="test_cases"):
        _parse_test_cases('{"key": "value"}', expected_count=1)


def test_parse_test_cases_partial_results_raises_validation_error() -> None:
    data = [MOCK_TEST_CASES_RAW[0]]
    with pytest.raises(GenerationValidationError, match="expected 5"):
        _parse_test_cases(json.dumps({"test_cases": data}), expected_count=5)


def test_parse_test_cases_legacy_raw_array() -> None:
    parsed = _parse_test_cases(json.dumps(MOCK_TEST_CASES_RAW), expected_count=10)
    assert len(parsed) == 10


def test_parse_test_cases_requires_persona_sections() -> None:
    data = [dict(MOCK_TEST_CASES_RAW[0], persona_context="A user. Be normal.")]
    with pytest.raises(GenerationValidationError, match="persona_context"):
        _parse_test_cases(json.dumps({"test_cases": data}), expected_count=1)


def test_parse_test_cases_requires_short_name() -> None:
    data = [
        dict(
            MOCK_TEST_CASES_RAW[0],
            name="Customer With A Very Long And Overly Specific Scheduling Problem",
        )
    ]
    with pytest.raises(GenerationValidationError, match="name"):
        _parse_test_cases(json.dumps({"test_cases": data}), expected_count=1)


def test_parse_test_cases_requires_tool_mock_responses() -> None:
    data = [
        dict(
            MOCK_TEST_CASES_RAW[0],
            expected_tool_calls=[{"tool": "test_tool", "expected_params": {"id": "1"}}],
        )
    ]
    with pytest.raises(GenerationValidationError, match="mock_responses"):
        _parse_test_cases(json.dumps({"test_cases": data}), expected_count=1)


def test_parse_test_cases_validates_required_tool_params() -> None:
    data = [
        dict(
            MOCK_TEST_CASES_RAW[0],
            expected_tool_calls=[
                {
                    "tool": "test_tool",
                    "expected_params": {},
                    "mock_responses": [
                        {"expected_params": {}, "response": {"ok": True}}
                    ],
                }
            ],
        )
    ]
    with pytest.raises(GenerationValidationError, match="required params"):
        _parse_test_cases(
            json.dumps({"test_cases": data}),
            expected_count=1,
            tools=[_test_tool()],
        )


def test_parse_test_cases_requires_mock_params_to_match_expected_params() -> None:
    data = [
        dict(
            MOCK_TEST_CASES_RAW[1],
            expected_tool_calls=[
                {
                    "tool": "test_tool",
                    "expected_params": {"id": "1"},
                    "mock_responses": [
                        {"expected_params": {"id": "2"}, "response": {"ok": True}}
                    ],
                }
            ],
        )
    ]
    with pytest.raises(GenerationValidationError, match="must match expected_params"):
        _parse_test_cases(
            json.dumps({"test_cases": data}),
            expected_count=1,
            tools=[_test_tool()],
        )


def test_parse_test_cases_allows_null_mock_params_for_no_param_tools() -> None:
    data = [
        dict(
            MOCK_TEST_CASES_RAW[1],
            expected_tool_calls=[
                {
                    "tool": "test_tool",
                    "expected_params": {},
                    "mock_responses": [
                        {"expected_params": None, "response": {"ok": True}}
                    ],
                }
            ],
        )
    ]

    parsed = _parse_test_cases(
        json.dumps({"test_cases": data}),
        expected_count=1,
        tools=[_no_param_tool()],
    )

    assert parsed[0].expected_tool_calls is not None
    assert parsed[0].expected_tool_calls[0].mock_responses is not None
    assert parsed[0].expected_tool_calls[0].mock_responses[0].expected_params is None


def test_parse_test_cases_rejects_null_mock_params_for_required_param_tools() -> None:
    data = [
        dict(
            MOCK_TEST_CASES_RAW[1],
            expected_tool_calls=[
                {
                    "tool": "test_tool",
                    "expected_params": {"id": "1"},
                    "mock_responses": [
                        {"expected_params": None, "response": {"ok": True}}
                    ],
                }
            ],
        )
    ]

    with pytest.raises(GenerationValidationError, match="include required params"):
        _parse_test_cases(
            json.dumps({"test_cases": data}),
            expected_count=1,
            tools=[_test_tool()],
        )


def test_parse_test_cases_rejects_tool_calls_without_tools() -> None:
    with pytest.raises(GenerationValidationError, match="agent has no tools"):
        _parse_test_cases(MOCK_LLM_RESPONSE, expected_count=10, tools=[])


@pytest.mark.asyncio
async def test_generate_test_cases_calls_llm() -> None:
    request = GenerateRequest(
        agent_prompt="You are a test agent.",
        tools=[_test_tool()],
        count=10,
    )
    with patch(
        "app.services.test_case_generator.batch.core.call_llm",
        new_callable=AsyncMock,
        return_value=_fake_llm_response(),
    ) as mock_call:
        created, model_used, latency_ms = await generate_test_cases(request)

    assert len(created) == 10
    assert latency_ms == 1500
    assert model_used == "gpt-4o"
    mock_call.assert_awaited_once()
    assert mock_call.await_args is not None
    call_config = mock_call.await_args.kwargs["config"]
    assert call_config.response_format is not None


@pytest.mark.asyncio
async def test_generate_test_cases_uses_config_default_model() -> None:
    request = GenerateRequest(
        agent_prompt="You are a test agent.",
        tools=[_test_tool()],
        count=10,
    )
    with (
        patch(
            "app.services.test_case_generator.batch.core.call_llm",
            new_callable=AsyncMock,
            return_value=_fake_llm_response(),
        ),
        patch("app.services.test_case_generator.batch.core.settings") as mock_settings,
    ):
        mock_settings.default_llm_id = "openai/gpt-4o"
        mock_settings.GENERATOR_MAX_TOKENS = 16_000
        _, model_used, _ = await generate_test_cases(request)

    assert model_used == "gpt-4o"


@pytest.mark.asyncio
async def test_generate_test_cases_respects_model_override() -> None:
    request = GenerateRequest(
        agent_prompt="You are a test agent.",
        tools=[_test_tool()],
        count=10,
        model="gpt-4o-mini",
    )
    resp = _fake_llm_response()
    resp.model = "gpt-4o-mini"
    with (
        patch(
            "app.services.test_case_generator.batch.core.call_llm",
            new_callable=AsyncMock,
            return_value=resp,
        ) as mock_call,
        patch("app.services.test_case_generator.batch.core.settings") as mock_settings,
    ):
        mock_settings.default_llm_id = "openai/gpt-4o"
        mock_settings.GENERATOR_MAX_TOKENS = 16_000
        _, model_used, _ = await generate_test_cases(request)

    assert model_used == "gpt-4o-mini"
    # Verify the config passed to call_llm has the override model
    assert mock_call.await_args is not None
    call_config = mock_call.await_args.kwargs.get("config") or mock_call.await_args[1]
    assert call_config.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_generate_test_cases_repairs_invalid_first_response() -> None:
    request = GenerateRequest(
        agent_prompt="You are a test agent.",
        tools=[_test_tool()],
        count=10,
    )
    invalid_cases = list(MOCK_TEST_CASES_RAW)
    invalid_cases[0] = dict(MOCK_TEST_CASES_RAW[0], persona_context="Bad")
    invalid_response = _fake_llm_response(json.dumps({"test_cases": invalid_cases}))
    repaired_response = _fake_llm_response(
        json.dumps({"test_cases": [MOCK_TEST_CASES_RAW[0]]})
    )
    repaired_response.latency_ms = 2000

    with patch(
        "app.services.test_case_generator.batch.core.call_llm",
        new_callable=AsyncMock,
        side_effect=[invalid_response, repaired_response],
    ) as mock_call:
        created, model_used, latency_ms = await generate_test_cases(request)

    assert len(created) == 10
    assert model_used == "gpt-4o"
    assert latency_ms == 3500
    assert mock_call.await_count == 2
    assert created[0].persona_context == MOCK_TEST_CASES_RAW[0]["persona_context"]
    assert created[1].name == MOCK_TEST_CASES_RAW[1]["name"]
    assert mock_call.await_args is not None
    repair_messages = mock_call.await_args.kwargs["messages"]
    assert "Regenerate ONLY these failed" in repair_messages[-1].content
    assert "test_cases[0]" in repair_messages[-1].content
    assert "test_cases[1]" not in repair_messages[-1].content
