"""Strip mock_response payloads for terminating tools before persisting UI-facing cases."""

from app.models.schemas import ExpectedToolCall
from app.models.test_case import TestCaseCreate
from app.services.agent_tool_definitions import AgentToolDefinition

ToolDefinition = AgentToolDefinition


def strip_mock_responses_for_terminating_tools(
    test_case: TestCaseCreate,
    *,
    tools: list[ToolDefinition] | None,
) -> TestCaseCreate:
    """Set ``mock_response`` to ``None`` for rows whose ``tool`` is terminating on the snapshot."""
    terminating = {t.name for t in tools or [] if t.terminating}
    if not terminating:
        return test_case

    etc = test_case.expected_tool_calls
    if not etc:
        return test_case

    new_calls: list[ExpectedToolCall] = []
    changed = False
    for row in etc:
        if row.tool in terminating and row.mock_response is not None:
            new_calls.append(row.model_copy(update={"mock_response": None}))
            changed = True
        else:
            new_calls.append(row)

    if not changed:
        return test_case
    return test_case.model_copy(update={"expected_tool_calls": new_calls})


def strip_mock_responses_for_terminating_tools_in_list(
    test_cases: list[TestCaseCreate],
    *,
    tools: list[ToolDefinition] | None,
) -> list[TestCaseCreate]:
    return [
        strip_mock_responses_for_terminating_tools(tc, tools=tools) for tc in test_cases
    ]
