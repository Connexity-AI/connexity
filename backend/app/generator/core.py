import json
import logging
import re

from app.core.config import settings
from app.generator.prompt import build_system_prompt, build_user_prompt
from app.generator.schemas import GenerateRequest
from app.models.scenario import ScenarioCreate
from app.services.llm import LLMCallConfig, LLMMessage, LLMResponse, call_llm

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^\s*```\w*\s*\n(.*?)\n\s*```\s*$", re.DOTALL)


async def generate_scenarios(
    request: GenerateRequest,
) -> tuple[list[ScenarioCreate], str, int]:
    """Generate scenarios from agent prompt.

    Returns (scenarios, model_used, latency_ms).
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

    scenarios = _parse_scenarios(response.content, expected_count=request.count)
    latency_ms = response.latency_ms or 0
    return scenarios, response.model, latency_ms


def _parse_scenarios(raw: str, expected_count: int) -> list[ScenarioCreate]:
    """Parse LLM JSON output into validated ScenarioCreate objects."""
    text = raw.strip()

    # Strip markdown code fences if present
    match = _FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()

    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("LLM response is not a JSON array")

    scenarios: list[ScenarioCreate] = []
    for item in data:
        # Force status to draft without mutating the original dict
        scenario = ScenarioCreate.model_validate({**item, "status": "draft"})
        scenarios.append(scenario)

    if len(scenarios) < expected_count:
        logger.warning(
            "LLM produced %d scenarios, expected %d", len(scenarios), expected_count
        )

    return scenarios
