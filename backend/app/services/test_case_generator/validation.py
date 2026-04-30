"""Shared quality validation for generated test cases."""

from app.models.test_case import TestCaseCreate
from app.services.test_case_generator.batch.schemas import ToolDefinition

PERSONA_SECTION_LABELS = (
    "[Persona type]",
    "[Description]",
    "[Behavioral instructions]",
)
MAX_TEST_CASE_NAME_CHARS = 60
MAX_TEST_CASE_NAME_WORDS = 7


class GenerationValidationError(ValueError):
    """Generated test cases parsed but failed quality checks."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validation_errors_from_exception(exc: Exception) -> list[str]:
    if isinstance(exc, GenerationValidationError):
        return exc.errors
    return [str(exc)]


def _required_params_by_tool(tools: list[ToolDefinition] | None) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for tool in tools or []:
        params = tool.parameters if isinstance(tool.parameters, dict) else {}
        required = params.get("required")
        out[tool.name] = (
            {item for item in required if isinstance(item, str)}
            if isinstance(required, list)
            else set()
        )
    return out


def _known_tool_names(tools: list[ToolDefinition] | None) -> set[str]:
    return {tool.name for tool in tools or []}


def _validate_persona_context(tc: TestCaseCreate, index: int) -> list[str]:
    persona = tc.persona_context or ""
    missing = [label for label in PERSONA_SECTION_LABELS if label not in persona]
    if not missing:
        return []
    return [
        "test_cases[%d].persona_context is missing required sections: %s"
        % (index, ", ".join(missing))
    ]


def _validate_name(tc: TestCaseCreate, index: int) -> list[str]:
    name = tc.name.strip()
    if not name:
        return [f"test_cases[{index}].name must not be empty"]
    if len(name) > MAX_TEST_CASE_NAME_CHARS:
        return [
            f"test_cases[{index}].name must be at most "
            f"{MAX_TEST_CASE_NAME_CHARS} characters"
        ]
    if len(name.split()) > MAX_TEST_CASE_NAME_WORDS:
        return [
            f"test_cases[{index}].name must be at most "
            f"{MAX_TEST_CASE_NAME_WORDS} words"
        ]
    return []


def _validate_expected_tool_calls(
    tc: TestCaseCreate,
    index: int,
    *,
    tools: list[ToolDefinition] | None,
) -> list[str]:
    expected_calls = tc.expected_tool_calls or []
    if not expected_calls:
        return []
    if tools is not None and not tools:
        return [
            f"test_cases[{index}].expected_tool_calls must be empty because "
            "the agent has no tools"
        ]

    known_names = _known_tool_names(tools)
    required_by_tool = _required_params_by_tool(tools)
    errors: list[str] = []

    for call_index, call in enumerate(expected_calls):
        prefix = f"test_cases[{index}].expected_tool_calls[{call_index}]"
        if known_names and call.tool not in known_names:
            errors.append(f"{prefix}.tool references unknown tool '{call.tool}'")

        required = required_by_tool.get(call.tool, set())
        expected_params = call.expected_params or {}
        missing_params = sorted(required.difference(expected_params.keys()))
        if missing_params:
            errors.append(
                f"{prefix}.expected_params is missing required params: "
                f"{', '.join(missing_params)}"
            )

        if not call.mock_responses:
            errors.append(f"{prefix}.mock_responses must include at least one response")
            continue

        for mock_index, mock_response in enumerate(call.mock_responses):
            mock_prefix = f"{prefix}.mock_responses[{mock_index}]"
            if mock_response.expected_params is None:
                if required:
                    errors.append(
                        f"{mock_prefix}.expected_params must include required params: "
                        f"{', '.join(sorted(required))}"
                    )
                continue

            missing_mock_params = sorted(
                required.difference(mock_response.expected_params.keys())
            )
            if missing_mock_params:
                errors.append(
                    f"{mock_prefix}.expected_params is missing required params: "
                    f"{', '.join(missing_mock_params)}"
                )
            else:
                mismatched_params = [
                    param
                    for param in sorted(required)
                    if mock_response.expected_params.get(param)
                    != expected_params.get(param)
                ]
                if mismatched_params:
                    errors.append(
                        f"{mock_prefix}.expected_params must match expected_params "
                        f"for required params: {', '.join(mismatched_params)}"
                    )

            if not mock_response.response:
                errors.append(f"{mock_prefix}.response must not be empty")

    return errors


def validate_test_case(
    tc: TestCaseCreate,
    index: int,
    *,
    tools: list[ToolDefinition] | None,
) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_name(tc, index))
    errors.extend(_validate_persona_context(tc, index))
    errors.extend(_validate_expected_tool_calls(tc, index, tools=tools))
    return errors


def validate_generated_cases(
    test_cases: list[TestCaseCreate],
    *,
    tools: list[ToolDefinition] | None,
    expected_count: int | None = None,
) -> None:
    errors: list[str] = []
    if expected_count is not None and len(test_cases) != expected_count:
        errors.append(
            f"LLM produced {len(test_cases)} test cases, expected {expected_count}"
        )

    for index, tc in enumerate(test_cases):
        errors.extend(validate_test_case(tc, index, tools=tools))

    if errors:
        raise GenerationValidationError(errors)
