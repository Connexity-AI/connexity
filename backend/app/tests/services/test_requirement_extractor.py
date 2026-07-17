import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm import LLMResponse
from app.services.requirement_extractor import (
    RequirementExtractionError,
    RequirementSource,
    _build_user_prompt,
    extract_requirements,
)


def _llm_response(payload: dict) -> LLMResponse:
    return LLMResponse(
        content=json.dumps(payload),
        model="test-model",
        latency_ms=10,
    )


@pytest.mark.asyncio
async def test_extracts_requirements_from_single_prompt() -> None:
    fake = _llm_response(
        {
            "requirements": [
                {"text": "Greet the caller", "category": "persona", "source_ref": None},
                {
                    "text": "Never disclose account PIN",
                    "category": "guardrail",
                    "source_ref": "Security",
                },
            ]
        }
    )
    source = RequirementSource(
        agent_name="Support Bot",
        system_prompt="You are a support agent. Greet warmly. Never reveal PINs.",
    )
    with patch(
        "app.services.requirement_extractor.call_llm",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        result = await extract_requirements(source=source)

    assert [r.text for r in result] == [
        "Greet the caller",
        "Never disclose account PIN",
    ]
    assert result[1].category == "guardrail"
    assert result[1].source_ref == "Security"


@pytest.mark.asyncio
async def test_empty_source_skips_llm_call() -> None:
    source = RequirementSource(agent_name="Empty")
    with patch(
        "app.services.requirement_extractor.call_llm", new_callable=AsyncMock
    ) as mock_llm:
        result = await extract_requirements(source=source)
    assert result == []
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_parse_failure_raises() -> None:
    bad = LLMResponse(content="not json", model="m", latency_ms=1)
    source = RequirementSource(system_prompt="do things")
    with patch(
        "app.services.requirement_extractor.call_llm",
        new_callable=AsyncMock,
        return_value=bad,
    ):
        with pytest.raises(RequirementExtractionError):
            await extract_requirements(source=source)


@pytest.mark.asyncio
async def test_llm_failure_raises() -> None:
    source = RequirementSource(system_prompt="do things")
    with patch(
        "app.services.requirement_extractor.call_llm",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RequirementExtractionError):
            await extract_requirements(source=source)


@pytest.mark.asyncio
async def test_dedupes_and_normalizes_unknown_category() -> None:
    fake = _llm_response(
        {
            "requirements": [
                {"text": "Confirm the appointment", "category": "made-up"},
                {"text": "confirm the appointment", "category": "capability"},
                {"text": "Offer to reschedule", "category": "capability"},
            ]
        }
    )
    source = RequirementSource(system_prompt="schedule appointments")
    with patch(
        "app.services.requirement_extractor.call_llm",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        result = await extract_requirements(source=source)

    # Case-insensitive dedupe drops the second item; unknown category -> "other".
    assert [r.text for r in result] == [
        "Confirm the appointment",
        "Offer to reschedule",
    ]
    assert result[0].category == "other"


def test_flow_source_renders_nodes_and_edges_in_prompt() -> None:
    source = RequirementSource(
        agent_name="Flow Agent",
        global_prompt="Be concise.",
        nodes=[
            {
                "id": "n1",
                "name": "Greeting",
                "type": "conversation",
                "instruction": {"type": "prompt", "text": "Greet the caller by name."},
            },
            {
                "id": "n2",
                "type": "branch",
                "name": "Router",
            },  # no instruction -> skipped
        ],
        edges=[
            {
                "transition_condition": {"prompt": "caller wants a refund"},
                "destination_node_id": "n_refund",
            }
        ],
        tools=[
            {"function": {"name": "lookup_order", "description": "Look up an order"}}
        ],
    )
    prompt = _build_user_prompt(source)
    assert "Be concise." in prompt
    assert "Greet the caller by name." in prompt
    assert "Router" not in prompt  # branch node without instruction excluded
    assert "caller wants a refund" in prompt
    assert "lookup_order" in prompt
