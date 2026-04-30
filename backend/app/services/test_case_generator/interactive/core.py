"""Single-turn LLM agent with tool calls for test case create/edit."""

import logging
from dataclasses import dataclass
from typing import Any, ClassVar

from app.core.config import settings
from app.models.test_case import TestCaseCreate
from app.services.llm import (
    LLMCallConfig,
    LLMMessage,
    LLMResponse,
    LLMSettingsView,
    call_llm,
)
from app.services.test_case_generator.interactive.context import AgentContext
from app.services.test_case_generator.interactive.prompt import (
    build_agent_messages,
    build_repair_user_prompt,
)
from app.services.test_case_generator.interactive.schemas import AgentMode
from app.services.test_case_generator.interactive.tools import (
    CREATE_TEST_CASE_TOOL,
    EDIT_TEST_CASE_TOOL,
    parse_create_test_case_tool_call_slots,
    parse_create_test_case_tool_calls,
    parse_edit_test_case_tool_call,
)
from app.services.test_case_generator.validation import (
    GenerationValidationError,
    validate_generated_cases,
    validate_test_case,
    validation_errors_from_exception,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TestCaseAgentInput:
    # Prevent pytest from collecting this dataclass as a test class.
    __test__: ClassVar[bool] = False

    mode: AgentMode
    user_message: str
    context: AgentContext
    llm_provider: str | None = None
    llm_model: str | None = None
    temperature: float | None = None


@dataclass
class TestCaseAgentOutput:
    __test__: ClassVar[bool] = False

    mode: AgentMode
    created: list[TestCaseCreate]
    edited: TestCaseCreate | None
    model_used: str
    latency_ms: int
    token_usage: dict[str, int] | None
    cost_usd: float | None


@dataclass(frozen=True)
class PartialCreateGeneration:
    created: list[TestCaseCreate | None]
    errors: list[str]
    failed_indices: list[int]


def _count_tool_calls(tool_calls: list[dict[str, Any]] | None, name: str) -> int:
    if not tool_calls:
        return 0
    count = 0
    for tc in tool_calls:
        fn = tc.get("function")
        if isinstance(fn, dict) and fn.get("name") == name:
            count += 1
    return count


def _merge_usage(
    first: dict[str, int] | None, second: dict[str, int] | None
) -> dict[str, int] | None:
    if not first and not second:
        return None
    out: dict[str, int] = {}
    for usage in (first or {}, second or {}):
        for key, value in usage.items():
            out[key] = out.get(key, 0) + value
    return out


def _merge_cost(first: float | None, second: float | None) -> float | None:
    if first is None and second is None:
        return None
    return (first or 0.0) + (second or 0.0)


def _tool_call_summary(tool_calls: list[dict[str, Any]] | None) -> list[str]:
    if not tool_calls:
        return []
    out: list[str] = []
    for tc in tool_calls:
        fn = tc.get("function")
        if isinstance(fn, dict):
            out.append(str(fn.get("name", "<missing-name>")))
        else:
            out.append("<missing-function>")
    return out


class TestCaseAgent:
    """Runs one non-streaming LLM call with tools and parses results."""

    __test__ = False

    def __init__(self, inp: TestCaseAgentInput) -> None:
        self._inp = inp

    async def run(
        self, *, app_settings: LLMSettingsView | None = None
    ) -> TestCaseAgentOutput:
        static, dynamic, user_content = build_agent_messages(
            mode=self._inp.mode,
            user_message=self._inp.user_message,
            ctx=self._inp.context,
        )
        messages = [
            LLMMessage(role="system", content=static),
            LLMMessage(role="system", content=dynamic),
            LLMMessage(role="user", content=user_content),
        ]

        tools = (
            [CREATE_TEST_CASE_TOOL]
            if self._inp.mode in (AgentMode.CREATE, AgentMode.FROM_TRANSCRIPT)
            else [EDIT_TEST_CASE_TOOL]
        )

        temperature = (
            self._inp.temperature
            if self._inp.temperature is not None
            else settings.GENERATOR_TEMPERATURE
        )

        llm_config = LLMCallConfig(
            model=self._inp.llm_model,
            provider=self._inp.llm_provider,
            max_tokens=settings.GENERATOR_MAX_TOKENS,
            temperature=temperature,
            tools=tools,
            parallel_tool_calls=True,
            extra={"tool_choice": "required"},
        )

        response = await call_llm(
            messages,
            llm_config,
            app_settings=app_settings,
        )

        try:
            created, edited = self._parse_response(response.tool_calls)
        except (GenerationValidationError, ValueError) as exc:
            validation_errors = validation_errors_from_exception(exc)
            partial_create = self._partial_create_generation(response.tool_calls)
            logger.warning(
                "Interactive test-case agent output failed validation; attempting "
                "repair. mode=%s model=%s tool_calls=%s failed_indices=%s errors=%s",
                self._inp.mode,
                response.model,
                _tool_call_summary(response.tool_calls),
                partial_create.failed_indices if partial_create is not None else None,
                validation_errors,
            )
            repair_response = await self._repair(
                messages=messages,
                llm_config=llm_config,
                response=response,
                validation_errors=validation_errors,
                partial_create=partial_create,
                app_settings=app_settings,
            )
            try:
                created, edited = self._parse_repair_response(
                    repair_response.tool_calls, partial_create=partial_create
                )
            except (GenerationValidationError, ValueError) as repair_exc:
                logger.error(
                    "Interactive test-case agent repair failed validation. "
                    "mode=%s model=%s original_tool_calls=%s repair_tool_calls=%s "
                    "errors=%s",
                    self._inp.mode,
                    repair_response.model,
                    _tool_call_summary(response.tool_calls),
                    _tool_call_summary(repair_response.tool_calls),
                    validation_errors_from_exception(repair_exc),
                )
                raise

            return TestCaseAgentOutput(
                mode=self._inp.mode,
                created=created,
                edited=edited,
                model_used=repair_response.model,
                latency_ms=(
                    (response.latency_ms or 0) + (repair_response.latency_ms or 0)
                ),
                token_usage=_merge_usage(response.usage, repair_response.usage),
                cost_usd=_merge_cost(
                    response.response_cost_usd,
                    repair_response.response_cost_usd,
                ),
            )

        return TestCaseAgentOutput(
            mode=self._inp.mode,
            created=created,
            edited=edited,
            model_used=response.model,
            latency_ms=response.latency_ms or 0,
            token_usage=dict(response.usage) if response.usage else None,
            cost_usd=response.response_cost_usd,
        )

    def _parse_response(
        self,
        raw_calls: list[dict[str, Any]] | None,
        *,
        expected_create_count: int | None = None,
    ) -> tuple[list[TestCaseCreate], TestCaseCreate | None]:
        if self._inp.mode in (AgentMode.CREATE, AgentMode.FROM_TRANSCRIPT):
            created = parse_create_test_case_tool_calls(raw_calls)
            raw_count = _count_tool_calls(raw_calls, "create_test_case")
            errors: list[str] = []

            if raw_count == 0:
                errors.append("LLM returned no create_test_case tool calls")
            elif len(created) != raw_count:
                errors.append(
                    "LLM returned %d valid create_test_case payload(s) out of %d call(s)"
                    % (len(created), raw_count)
                )

            try:
                validate_generated_cases(
                    created,
                    tools=self._inp.context.tools,
                    expected_count=expected_create_count,
                )
            except GenerationValidationError as exc:
                errors.extend(exc.errors)

            if errors:
                raise GenerationValidationError(errors)
            return created, None

        edited = parse_edit_test_case_tool_call(raw_calls)
        raw_count = _count_tool_calls(raw_calls, "edit_test_case")
        errors = []

        if raw_count != 1:
            errors.append(
                f"LLM returned {raw_count} edit_test_case tool calls, expected 1"
            )
        if edited is None:
            errors.append("LLM returned no valid edit_test_case payload")
        else:
            errors.extend(validate_test_case(edited, 0, tools=self._inp.context.tools))

        if errors:
            raise GenerationValidationError(errors)
        return [], edited

    def _partial_create_generation(
        self, raw_calls: list[dict[str, Any]] | None
    ) -> PartialCreateGeneration | None:
        if self._inp.mode not in (AgentMode.CREATE, AgentMode.FROM_TRANSCRIPT):
            return None

        slots = parse_create_test_case_tool_call_slots(raw_calls)
        if not slots:
            return None

        errors: list[str] = []
        valid_slots: list[TestCaseCreate | None] = []
        for index, tc in enumerate(slots):
            if tc is None:
                errors.append(f"test_cases[{index}] failed schema validation")
                valid_slots.append(None)
                continue

            case_errors = validate_test_case(tc, index, tools=self._inp.context.tools)
            if case_errors:
                errors.extend(case_errors)
                valid_slots.append(None)
            else:
                valid_slots.append(tc)

        failed_indices = [
            index for index, test_case in enumerate(valid_slots) if test_case is None
        ]
        return PartialCreateGeneration(
            created=valid_slots,
            errors=errors,
            failed_indices=failed_indices,
        )

    def _merge_partial_create_generation(
        self,
        partial_create: PartialCreateGeneration,
        repaired: list[TestCaseCreate],
    ) -> list[TestCaseCreate]:
        if len(repaired) != len(partial_create.failed_indices):
            raise GenerationValidationError(
                [
                    "LLM produced %d repaired test cases, expected %d"
                    % (len(repaired), len(partial_create.failed_indices))
                ]
            )

        merged = list(partial_create.created)
        for index, repaired_case in zip(
            partial_create.failed_indices, repaired, strict=True
        ):
            merged[index] = repaired_case

        if any(case is None for case in merged):
            missing = [
                f"test_cases[{index}]"
                for index, case in enumerate(merged)
                if case is None
            ]
            raise GenerationValidationError(
                [f"Repair did not replace all failed cases: {', '.join(missing)}"]
            )

        return [case for case in merged if case is not None]

    def _parse_repair_response(
        self,
        raw_calls: list[dict[str, Any]] | None,
        *,
        partial_create: PartialCreateGeneration | None,
    ) -> tuple[list[TestCaseCreate], TestCaseCreate | None]:
        if partial_create is None or not partial_create.failed_indices:
            expected_count = self._expected_repair_create_count(raw_calls)
            return self._parse_response(raw_calls, expected_create_count=expected_count)

        repair_count = _count_tool_calls(raw_calls, "create_test_case")
        original_count = len(partial_create.created)
        failed_count = len(partial_create.failed_indices)

        if repair_count == original_count:
            return self._parse_response(raw_calls, expected_create_count=original_count)

        repaired, _ = self._parse_response(
            raw_calls, expected_create_count=failed_count
        )
        return self._merge_partial_create_generation(partial_create, repaired), None

    def _expected_repair_create_count(
        self, raw_calls: list[dict[str, Any]] | None
    ) -> int | None:
        if self._inp.mode not in (AgentMode.CREATE, AgentMode.FROM_TRANSCRIPT):
            return None
        raw_count = _count_tool_calls(raw_calls, "create_test_case")
        return raw_count or None

    async def _repair(
        self,
        *,
        messages: list[LLMMessage],
        llm_config: LLMCallConfig,
        response: LLMResponse,
        validation_errors: list[str],
        partial_create: PartialCreateGeneration | None,
        app_settings: LLMSettingsView | None,
    ) -> LLMResponse:
        expected_count = (
            len(partial_create.failed_indices)
            if partial_create is not None and partial_create.failed_indices
            else self._expected_repair_create_count(response.tool_calls)
        )
        repair_prompt = build_repair_user_prompt(
            mode=self._inp.mode,
            validation_errors=validation_errors,
            previous_tool_calls=response.tool_calls,
            expected_create_count=expected_count,
            failed_indices=(
                partial_create.failed_indices if partial_create is not None else None
            ),
        )
        return await call_llm(
            [
                *messages,
                LLMMessage(role="user", content=repair_prompt),
            ],
            llm_config,
            app_settings=app_settings,
        )
