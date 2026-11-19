"""The tools a Retell version declares, read once per run so a test fakes every tool
but the ones that end the call (plan `plans/2026-11-19-simulations-finish.md`)."""

from app.services.component_versions import RetellTool, _tools_in


def test_a_single_prompts_tools_and_its_states_tools_are_read_once_each() -> None:
    llm = {
        "general_tools": [
            {"type": "end_call", "name": "end_call"},
            {"type": "custom", "name": "check_slot"},
        ],
        "states": [
            {"name": "booking", "tools": [{"type": "custom", "name": "book_slot"}]},
            {"name": "again", "tools": [{"type": "custom", "name": "check_slot"}]},
        ],
    }

    assert _tools_in(llm) == [
        RetellTool(name="end_call", ends_call=True),
        RetellTool(name="check_slot", ends_call=False),
        RetellTool(name="book_slot", ends_call=False),
    ]


def test_a_flows_tools_are_read_and_a_transfer_ends_the_call() -> None:
    flow = {
        "tools": [
            {"type": "custom", "name": "lookup_order", "tool_id": "t1"},
            {"type": "transfer_call", "name": "to_human", "tool_id": "t2"},
        ],
        "nodes": [{"type": "end", "id": "n9"}],
    }

    assert _tools_in(flow) == [
        RetellTool(name="lookup_order", ends_call=False),
        RetellTool(name="to_human", ends_call=True),
    ]


def test_nothing_readable_declares_no_tools() -> None:
    assert _tools_in(None) == []
    assert _tools_in({"general_tools": [{"type": "custom"}, "odd"]}) == []
