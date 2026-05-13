"""Shared quality validation for generated test cases."""

import re
from typing import Any

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


def _terminating_tool_names(tools: list[ToolDefinition] | None) -> set[str]:
    return {t.name for t in tools or [] if t.terminating}


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


_PARAM_PLACEHOLDER_RE = re.compile(r"^\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}$")
_SINGLE_BRACE_NAME_RE = re.compile(r"^\{[a-zA-Z_][a-zA-Z0-9_]*\}$")

_MALFORMED_PLACEHOLDER_MSG = (
    "malformed placeholder: use exactly {{paramName}} "
    "(letters, digits, underscore); one token per string, no spaces or extra text"
)


def _param_placeholder_syntax_error(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if _PARAM_PLACEHOLDER_RE.match(value):
        return None
    if "{{" in value or "}}" in value:
        return _MALFORMED_PLACEHOLDER_MSG
    if _SINGLE_BRACE_NAME_RE.match(value):
        return _MALFORMED_PLACEHOLDER_MSG
    return None


def _collect_placeholder_syntax_errors(
    params: dict[str, Any],
    *,
    base_path: str,
) -> list[str]:
    errors: list[str] = []

    def walk(obj: Any, path: str) -> None:
        err = _param_placeholder_syntax_error(obj)
        if err:
            errors.append(f"{path}: {err}")
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                walk(item, f"{path}[{i}]")

    for key, val in params.items():
        walk(val, f"{base_path}.{key}")
    return errors


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
    terminating_names = _terminating_tool_names(tools)
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
        else:
            errors.extend(
                _collect_placeholder_syntax_errors(
                    expected_params,
                    base_path=f"{prefix}.expected_params",
                )
            )

        terminating = call.tool in terminating_names
        if terminating:
            if call.mock_response is not None and not isinstance(
                call.mock_response, dict
            ):
                errors.append(f"{prefix}.mock_response must be an object or omitted")
            continue

        if call.mock_response is None:
            errors.append(f"{prefix}.mock_response must be set to a JSON object")
        elif not isinstance(call.mock_response, dict):
            errors.append(f"{prefix}.mock_response must be an object")

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
