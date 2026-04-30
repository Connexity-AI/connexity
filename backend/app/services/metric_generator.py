"""LLM-assisted generation of custom judge metric definitions."""

import json
import logging
import re

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.models.enums import MetricTier, ScoreType
from app.services.llm import LLMCallConfig, LLMMessage, call_llm

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^\s*```\w*\s*\n(.*?)\n\s*```\s*$", re.DOTALL)
_MEASURES_RE = re.compile(r"^measures:\s*(.+)", re.IGNORECASE)


class MetricGenerateRequest(BaseModel):
    description: str = Field(
        min_length=1,
        description="What the metric should measure (natural language)",
    )
    score_type: ScoreType | None = Field(
        default=None,
        description="Force scored (0-5) or binary; omit to let the model choose",
    )
    tier: MetricTier | None = Field(
        default=None,
        description="Force tier; omit to let the model choose",
    )
    model: str | None = Field(default=None, description="LLM model override")


class MetricGenerateResult(BaseModel):
    name: str
    display_name: str
    description: str
    tier: MetricTier
    default_weight: float = Field(ge=0.0)
    score_type: ScoreType
    rubric: str
    model_used: str
    generation_time_ms: int


def _name_to_display_name(name: str) -> str:
    return name.replace("_", " ").title()


def _extract_description(rubric: str) -> str:
    """Pull a one-sentence description from the rubric's 'Measures:' line."""
    for line in rubric.strip().splitlines():
        m = _MEASURES_RE.match(line.strip())
        if m:
            desc = m.group(1).strip()
            if desc:
                return desc[0].upper() + desc[1:]
    first_line = rubric.strip().split("\n", 1)[0].strip()
    return first_line if first_line else "Custom metric."


_SYSTEM_PROMPT = """\
You design evaluation rubrics for judging voice AI agent conversation transcripts.

## Output schema

Return a single JSON object with these keys:

- **name** — snake_case identifier (lowercase letters, digits, underscores; starts with a letter).
- **tier** — one of: execution, knowledge, process, delivery.
  - execution: tool usage, parameter accuracy, result handling.
  - knowledge: factual grounding, instruction/policy adherence.
  - process: information gathering, conversation flow, error recovery.
  - delivery: tone, conciseness, TTS-friendliness, phrasing.
- **score_type** — "scored" (0-5 integer scale) or "binary" (pass/fail).
- **rubric** — full rubric text following the format below.

## Rubric format

The rubric MUST begin with a "Measures:" line — one sentence summarizing what the metric evaluates.

### Scored metrics (0-5)

After the "Measures:" line, list score levels 5 → 0. Each level has a one-sentence \
criterion and a concrete "Example:" line.

```
Measures: <one-sentence summary of what is being evaluated>.

5: <criterion — flawless performance>
   Example: <realistic transcript situation>
4: <criterion — minor issue>
   Example: ...
3: <criterion — one meaningful problem>
   Example: ...
2: <criterion — significant problems>
   Example: ...
1: <criterion — mostly failing>
   Example: ...
0: <criterion — complete failure>
   Example: ...
```

Here is a real rubric for reference:

```
Measures: argument values correctly extracted from conversation for tools.

5: All parameters correct. Values accurately extracted from user input.
   Example: User said "next Tuesday at 2pm" — agent passed correct date and time.
4: All critical parameters correct. One minor parameter slightly off but doesn't affect outcome.
   Example: Name passed as "Bob" instead of "Bobby" (user used both).
3: One critical parameter wrong or missing, affecting tool outcome.
   Example: Date extracted as March 30 when user said March 31.
2: Multiple parameter errors. Tool may have returned wrong results or failed.
   Example: Wrong date + wrong service type passed to booking tool.
1: Most parameters fabricated or missing. Values not grounded in conversation.
   Example: Agent invented a phone number not mentioned by user.
0: No parameters extracted from conversation. All values fabricated or empty.
   Example: Tool called with all default/placeholder values.
```

### Binary metrics (pass/fail)

After the "Measures:" line, define Pass and Fail conditions each with an example.

```
Measures: <one-sentence summary>.

Pass: <clear pass condition>
Example: <realistic situation>
Fail: <clear fail condition>
Example: <realistic situation>
```

## Rubric quality rules

- Criteria must be observable from the conversation transcript alone — no hidden internal state.
- Use specific, measurable behaviors. Avoid vague words: "good", "appropriate", "adequate".
- Score levels must be strictly ordered with no gaps or overlaps between adjacent levels.
- Examples must be realistic voice AI customer-service situations (tool calls, user replies, agent responses).
"""


def _build_user_prompt(request: MetricGenerateRequest) -> str:
    constraints: list[str] = []
    if request.score_type is not None:
        constraints.append(f"- score_type must be **{request.score_type.value}**")
    if request.tier is not None:
        constraints.append(f"- tier must be **{request.tier.value}**")

    constraint_block = ""
    if constraints:
        constraint_block = "\n\nConstraints:\n" + "\n".join(constraints)

    return (
        f"Create a judge metric for:\n\n"
        f"{request.description.strip()}{constraint_block}"
    )


def _metric_response_format() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "generated_custom_metric",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "tier": {
                        "type": "string",
                        "enum": [
                            MetricTier.EXECUTION.value,
                            MetricTier.KNOWLEDGE.value,
                            MetricTier.PROCESS.value,
                            MetricTier.DELIVERY.value,
                        ],
                    },
                    "score_type": {
                        "type": "string",
                        "enum": [ScoreType.SCORED.value, ScoreType.BINARY.value],
                    },
                    "rubric": {"type": "string"},
                },
                "required": ["name", "tier", "score_type", "rubric"],
                "additionalProperties": False,
            },
        },
    }


def _parse_metric_json(raw: str) -> dict[str, object]:
    text = raw.strip()
    match = _FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        msg = "LLM metric response must be a JSON object"
        raise ValueError(msg)
    return data


async def generate_metric(request: MetricGenerateRequest) -> MetricGenerateResult:
    """Call the LLM to draft a metric definition (not persisted)."""
    llm_config = LLMCallConfig(
        model=request.model or settings.default_llm_id,
        max_tokens=settings.GENERATOR_MAX_TOKENS,
        temperature=settings.GENERATOR_TEMPERATURE,
        response_format=_metric_response_format(),
    )

    response = await call_llm(
        messages=[
            LLMMessage(role="system", content=_SYSTEM_PROMPT),
            LLMMessage(role="user", content=_build_user_prompt(request)),
        ],
        config=llm_config,
    )

    latency_ms = response.latency_ms or 0
    try:
        payload = _parse_metric_json(response.content or "")
        name = str(payload["name"])
        rubric = str(payload["rubric"])
        validated = MetricGenerateResult.model_validate(
            {
                "name": name,
                "display_name": _name_to_display_name(name),
                "description": _extract_description(rubric),
                "tier": payload["tier"],
                "default_weight": settings.GENERATOR_CUSTOM_METRIC_DEFAULT_WEIGHT,
                "score_type": payload["score_type"],
                "rubric": rubric,
                "model_used": response.model,
                "generation_time_ms": latency_ms,
            }
        )
    except (KeyError, json.JSONDecodeError, ValueError, ValidationError) as e:
        logger.warning("Metric generation parse/validation failed: %s", e)
        msg = f"Invalid metric JSON from LLM: {e}"
        raise ValueError(msg) from e

    return validated
