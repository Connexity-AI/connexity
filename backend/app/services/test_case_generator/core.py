import json
import logging
import re

from app.core.config import settings
from app.models.test_case import TestCaseCreate
from app.services.llm import LLMCallConfig, LLMMessage, LLMResponse, call_llm
from app.services.test_case_generator.prompt import (
    build_system_prompt,
    build_user_prompt,
)
from app.services.test_case_generator.schemas import GenerateRequest

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^\s*```\w*\s*\n(.*?)\n\s*```\s*$", re.DOTALL)


async def generate_test_cases(
    request: GenerateRequest,
) -> tuple[list[TestCaseCreate], str, int]:
    """Generate test cases from agent prompt.

    Returns (test_cases, model_used, latency_ms).
    """
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        agent_prompt=request.agent_prompt,
        tools=request.tools,
        count=request.count,
        focus_tags=request.focus_tags or None,
    )

    temperature = (
        request.temperature
        if request.temperature is not None
        else settings.GENERATOR_TEMPERATURE
    )

    llm_config = LLMCallConfig(
        model=request.model or settings.LLM_DEFAULT_MODEL,
        max_tokens=settings.GENERATOR_MAX_TOKENS,
        temperature=temperature,
    )

    response: LLMResponse = await call_llm(
        messages=[
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ],
        config=llm_config,
    )

    test_cases = _parse_test_cases(response.content, expected_count=request.count)
    latency_ms = response.latency_ms or 0
    return test_cases, response.model, latency_ms


def _parse_test_cases(raw: str, expected_count: int) -> list[TestCaseCreate]:
    """Parse LLM JSON output into validated TestCaseCreate objects."""
    text = raw.strip()

    match = _FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()

    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("LLM response is not a JSON array")

    test_cases: list[TestCaseCreate] = []
    for item in data:
        tc = TestCaseCreate.model_validate({**item, "status": "draft"})
        test_cases.append(tc)

    if len(test_cases) < expected_count:
        logger.warning(
            "LLM produced %d test cases, expected %d", len(test_cases), expected_count
        )

    return test_cases
