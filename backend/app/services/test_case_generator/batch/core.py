import json
import logging
import re
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.config import settings
from app.models.test_case import TestCaseCreate
from app.services.llm import LLMCallConfig, LLMMessage, LLMResponse, call_llm
from app.services.test_case_generator.batch.prompt import (
    build_partial_repair_user_prompt,
    build_repair_user_prompt,
    build_response_format,
    build_system_prompt,
    build_user_prompt,
)
from app.services.test_case_generator.batch.schemas import (
    GenerateRequest,
    ToolDefinition,
)
from app.services.test_case_generator.validation import (
    GenerationValidationError,
    validation_errors_from_exception,
)
from app.services.test_case_generator.validation import (
    validate_generated_cases as _validate_generated_cases,
)
from app.services.test_case_generator.validation import (
    validate_test_case as _validate_test_case,
)

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^\s*```\w*\s*\n(.*?)\n\s*```\s*$", re.DOTALL)


@dataclass(frozen=True)
class PartialGeneration:
    test_cases: list[TestCaseCreate | None]
    errors: list[str]
    failed_indices: list[int]


async def generate_test_cases(
    request: GenerateRequest,
) -> tuple[list[TestCaseCreate], str, int]:
    """Generate test cases from agent prompt.

    Returns (test_cases, model_used, latency_ms).
    """
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        agent_prompt=request.agent_prompt or "",
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
        model=request.model or settings.default_llm_id,
        max_tokens=settings.GENERATOR_MAX_TOKENS,
        temperature=temperature,
        response_format=build_response_format(),
    )

    response: LLMResponse = await call_llm(
        messages=[
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ],
        config=llm_config,
    )

    try:
        test_cases = _parse_test_cases(
            response.content,
            expected_count=request.count,
            tools=request.tools,
        )
        latency_ms = response.latency_ms or 0
        return test_cases, response.model, latency_ms
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        validation_errors = validation_errors_from_exception(exc)
        logger.warning(
            "Generated test cases failed validation; attempting repair: %s", exc
        )

    try:
        partial_generation = _parse_partial_test_cases(
            response.content,
            expected_count=request.count,
            tools=request.tools,
        )
    except (json.JSONDecodeError, ValidationError, ValueError):
        partial_generation = None

    if partial_generation is not None and partial_generation.failed_indices:
        repair_response = await call_llm(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
                LLMMessage(role="assistant", content=response.content),
                LLMMessage(
                    role="user",
                    content=build_partial_repair_user_prompt(
                        previous_output=response.content,
                        validation_errors=partial_generation.errors,
                        failed_indices=partial_generation.failed_indices,
                    ),
                ),
            ],
            config=llm_config,
        )

        repaired = _parse_test_cases(
            repair_response.content,
            expected_count=len(partial_generation.failed_indices),
            tools=request.tools,
        )
        merged = _merge_partial_generation(partial_generation, repaired)
        _validate_generated_cases(
            merged,
            expected_count=request.count,
            tools=request.tools,
        )
        latency_ms = (response.latency_ms or 0) + (repair_response.latency_ms or 0)
        return merged, repair_response.model, latency_ms

    repair_response: LLMResponse = await call_llm(
        messages=[
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
            LLMMessage(role="assistant", content=response.content),
            LLMMessage(
                role="user",
                content=build_repair_user_prompt(
                    previous_output=response.content,
                    validation_errors=validation_errors,
                    count=request.count,
                ),
            ),
        ],
        config=llm_config,
    )

    repaired = _parse_test_cases(
        repair_response.content,
        expected_count=request.count,
        tools=request.tools,
    )
    latency_ms = (response.latency_ms or 0) + (repair_response.latency_ms or 0)
    return repaired, repair_response.model, latency_ms


def _merge_partial_generation(
    partial_generation: PartialGeneration,
    repaired: list[TestCaseCreate],
) -> list[TestCaseCreate]:
    merged = list(partial_generation.test_cases)
    for index, repaired_case in zip(
        partial_generation.failed_indices, repaired, strict=True
    ):
        merged[index] = repaired_case

    if any(case is None for case in merged):
        missing = [
            f"test_cases[{index}]" for index, case in enumerate(merged) if case is None
        ]
        raise GenerationValidationError(
            [f"Repair did not replace all failed cases: {', '.join(missing)}"]
        )

    return [case for case in merged if case is not None]


def _parse_payload(raw: str) -> object:
    text = raw.strip()

    match = _FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()

    return json.loads(text)


def _extract_items(data: object) -> list[object]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        raw_items = data.get("test_cases")
        if isinstance(raw_items, list):
            return raw_items
    raise ValueError('LLM response is not a JSON object with a "test_cases" array')


def _parse_item(item: object, index: int) -> TestCaseCreate:
    if not isinstance(item, dict):
        msg = f"test_cases[{index}] is not a JSON object"
        raise ValueError(msg)
    # Drop any status the LLM may have emitted so the model default
    # (ACTIVE) applies; status is not part of the prompt schema.
    cleaned = {k: v for k, v in item.items() if k != "status"}
    return TestCaseCreate.model_validate(cleaned)


def _parse_partial_test_cases(
    raw: str,
    expected_count: int,
    tools: list[ToolDefinition] | None = None,
) -> PartialGeneration:
    """Parse valid cases and collect per-index errors for repair."""
    data = _parse_payload(raw)
    items = _extract_items(data)

    test_cases: list[TestCaseCreate | None] = [None] * expected_count
    errors: list[str] = []

    if len(items) > expected_count:
        errors.append(
            f"LLM produced {len(items)} test cases, expected {expected_count}"
        )

    for index in range(expected_count):
        if index >= len(items):
            errors.append(f"test_cases[{index}] is missing")
            continue
        try:
            tc = _parse_item(items[index], index)
        except (ValidationError, ValueError) as exc:
            errors.append(f"test_cases[{index}] failed schema validation: {exc}")
            continue

        case_errors = _validate_test_case(tc, index, tools=tools)
        if case_errors:
            errors.extend(case_errors)
            continue

        test_cases[index] = tc

    failed_indices = [
        index for index, test_case in enumerate(test_cases) if test_case is None
    ]
    return PartialGeneration(
        test_cases=test_cases,
        errors=errors,
        failed_indices=failed_indices,
    )


def _parse_test_cases(
    raw: str,
    expected_count: int,
    tools: list[ToolDefinition] | None = None,
) -> list[TestCaseCreate]:
    """Parse LLM JSON output into validated TestCaseCreate objects."""
    data = _parse_payload(raw)
    items = _extract_items(data)

    test_cases: list[TestCaseCreate] = []
    for index, item in enumerate(items):
        test_cases.append(_parse_item(item, index))

    _validate_generated_cases(test_cases, expected_count=expected_count, tools=tools)
    return test_cases
