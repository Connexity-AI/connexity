import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm import LLMResponse
from app.services.metric_generator import (
    MetricGenerateRequest,
    MetricTier,
    ScoreType,
    _extract_description,
    _parse_metric_json,
    generate_metric,
)


def test_extract_description_from_measures_line() -> None:
    rubric = "Measures: how well the agent confirms appointments.\n\n5: Great."
    assert _extract_description(rubric) == "How well the agent confirms appointments."


def test_extract_description_falls_back_to_first_line() -> None:
    rubric = "First line only rubric"
    assert _extract_description(rubric) == "First line only rubric"


def test_parse_metric_json_strips_fences() -> None:
    inner = json.dumps(
        {
            "name": "test_metric",
            "tier": "execution",
            "score_type": "scored",
            "rubric": "Measures: x.\n5: y.",
        }
    )
    wrapped = f"```json\n{inner}\n```"
    data = _parse_metric_json(wrapped)
    assert data["name"] == "test_metric"


def test_parse_metric_json_invalid_raises() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        _parse_metric_json("[]")


@pytest.mark.asyncio
async def test_generate_metric_parses_llm_response() -> None:
    payload = {
        "name": "booking_accuracy",
        "tier": MetricTier.EXECUTION.value,
        "score_type": ScoreType.SCORED.value,
        "rubric": (
            "Measures: correct booking details from the conversation.\n\n"
            "5: All fields match user statements.\n"
            "   Example: User said Tuesday 3pm; agent booked Tuesday 3pm."
        ),
    }
    fake = LLMResponse(
        content=json.dumps(payload),
        model="test-model",
        usage={},
        latency_ms=42,
    )
    with patch(
        "app.services.metric_generator.call_llm",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        result = await generate_metric(
            MetricGenerateRequest(description="Book appointments correctly")
        )
    assert result.name == "booking_accuracy"
    assert result.tier == MetricTier.EXECUTION
    assert result.score_type == ScoreType.SCORED
    assert result.model_used == "test-model"
    assert result.generation_time_ms == 42
    assert "Measures:" in result.rubric
    assert "booking" in result.description.lower()


@pytest.mark.asyncio
async def test_generate_metric_invalid_llm_payload_raises() -> None:
    fake = LLMResponse(
        content="not json",
        model="test-model",
        usage={},
        latency_ms=0,
    )
    with patch(
        "app.services.metric_generator.call_llm",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        with pytest.raises(ValueError, match="Invalid metric JSON"):
            await generate_metric(MetricGenerateRequest(description="x"))
