"""Retell's call list and agent list. Every response here is invented."""

import json
from datetime import UTC, datetime

import httpx
import pytest
import respx
from fastapi import HTTPException

from app.services import retell as retell_api
from app.services.retell import list_retell_agents, list_retell_calls
from app.tests.utils.retell_payloads import retell_call

LIST_CALLS = "https://api.retellai.com/v3/list-calls"
GET_CALL = "https://api.retellai.com/v2/get-call/"
LIST_AGENTS = "https://api.retellai.com/v2/list-agents"
AFTER = datetime(2026, 10, 9, 15, 40, 34, 336000, tzinfo=UTC)


def _list_item(call_id: str, status: str = "ended") -> dict:
    full = retell_call(call_id, agent_id="agent_invented_1")
    item = {k: v for k, v in full.items() if k not in ("transcript_with_tool_calls",)}
    item["call_status"] = status
    if status != "ended":
        item.pop("end_timestamp", None)
    return item


def _serve_calls() -> respx.Route:
    return respx.get(url__startswith=GET_CALL).mock(
        side_effect=lambda request: httpx.Response(
            200,
            json=retell_call(
                request.url.path.rsplit("/", 1)[-1], agent_id="agent_invented_1"
            ),
        )
    )


@respx.mock
async def test_a_pull_lists_by_agent_and_start_time_and_reads_each_finished_call() -> (
    None
):
    listing = respx.post(LIST_CALLS).mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    _list_item("call_a"),
                    _list_item("call_failed_to_connect", status="not_connected"),
                    _list_item("call_b"),
                    _list_item("call_live", status="ongoing"),
                    _list_item("call_c"),
                ],
                "has_more": False,
            },
        )
    )
    reads = _serve_calls()

    calls = await list_retell_calls(
        "key_invented", agent_id="agent_invented_1", start_after=AFTER, limit=100
    )

    sent = json.loads(listing.calls.last.request.content)
    assert sent["filter_criteria"]["agent"] == [{"agent_id": "agent_invented_1"}]
    assert sent["filter_criteria"]["start_timestamp"] == {
        "type": "number",
        "op": "gt",
        "value": int(AFTER.timestamp() * 1000),
    }
    assert (sent["sort_order"], sent["limit"]) == ("ascending", 100)
    assert listing.calls.last.request.headers["Authorization"] == "Bearer key_invented"

    # A call that never connected is skipped. The pull stops at the call still in
    # progress, so the next one starts before it and picks it up once it has ended.
    assert [c.call_id for c in calls] == ["call_a", "call_b"]
    assert reads.call_count == 2
    assert all("transcript_with_tool_calls" in (c.raw or {}) for c in calls)


@respx.mock
async def test_without_a_start_time_there_is_no_time_filter() -> None:
    listing = respx.post(LIST_CALLS).mock(
        return_value=httpx.Response(200, json={"items": [], "has_more": False})
    )
    assert await list_retell_calls("key_invented", agent_id="agent_invented_1") == []
    assert (
        "start_timestamp"
        not in json.loads(listing.calls.last.request.content)["filter_criteria"]
    )


@respx.mock
async def test_a_failed_full_read_stops_the_batch_before_that_call() -> None:
    respx.post(LIST_CALLS).mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    _list_item("call_a"),
                    _list_item("call_b"),
                    _list_item("call_c"),
                ],
                "has_more": False,
            },
        )
    )

    def answer(request: httpx.Request) -> httpx.Response:
        call_id = request.url.path.rsplit("/", 1)[-1]
        if call_id == "call_b":
            return httpx.Response(500, json={"message": "boom"})
        return httpx.Response(
            200, json=retell_call(call_id, agent_id="agent_invented_1")
        )

    respx.get(url__startswith=GET_CALL).mock(side_effect=answer)
    calls = await list_retell_calls("key_invented", agent_id="agent_invented_1")
    # call_c was read, but returning it would move the next pull past call_b.
    assert [c.call_id for c in calls] == ["call_a"]


@respx.mock
async def test_a_call_retell_no_longer_has_is_skipped() -> None:
    respx.post(LIST_CALLS).mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [_list_item("call_gone"), _list_item("call_b")],
                "has_more": False,
            },
        )
    )

    def answer(request: httpx.Request) -> httpx.Response:
        call_id = request.url.path.rsplit("/", 1)[-1]
        if call_id == "call_gone":
            return httpx.Response(404, json={"message": "not found"})
        return httpx.Response(
            200, json=retell_call(call_id, agent_id="agent_invented_1")
        )

    respx.get(url__startswith=GET_CALL).mock(side_effect=answer)
    calls = await list_retell_calls("key_invented", agent_id="agent_invented_1")
    assert [c.call_id for c in calls] == ["call_b"]


@respx.mock
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(
            400, json={"message": "Deprecated API usage is no longer supported"}
        ),
        httpx.Response(500, text="boom"),
        httpx.Response(200, text=""),
        httpx.Response(200, text="<html>"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={"calls": []}),
    ],
)
async def test_a_failed_empty_or_malformed_list_is_an_error(
    response: httpx.Response,
) -> None:
    respx.post(LIST_CALLS).mock(return_value=response)
    with pytest.raises(HTTPException) as raised:
        await list_retell_calls("key_invented", agent_id="agent_invented_1")
    assert raised.value.status_code == 502


@respx.mock
async def test_an_unreachable_or_slow_list_is_an_error() -> None:
    respx.post(LIST_CALLS).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(HTTPException) as raised:
        await list_retell_calls("key_invented", agent_id="agent_invented_1")
    assert raised.value.detail == "Failed to reach Retell API"


# ── Agents ─────────────────────────────────────────────────────────


@respx.mock
async def test_the_agent_list_reads_every_page_and_marks_published_agents() -> None:
    route = respx.post(LIST_AGENTS).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "agent_id": "agent_1",
                            "agent_name": "Booking",
                            "latest_published_version": 12,
                        },
                        {"agent_id": "agent_2", "agent_name": "Draft only"},
                    ],
                    "has_more": True,
                    "pagination_key": "page_2",
                },
            ),
            httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "agent_id": "agent_3",
                            "agent_name": "Inbound",
                            "latest_published_version": 3,
                        }
                    ],
                    "has_more": False,
                },
            ),
        ]
    )
    agents = await list_retell_agents("key_invented")
    assert [(a.agent_id, a.is_published, a.version) for a in agents] == [
        ("agent_1", True, 12),
        ("agent_2", False, None),
        ("agent_3", True, 3),
    ]
    assert route.calls[1].request.url.params["pagination_key"] == "page_2"


@respx.mock
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={"message": "bad key"}),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"agents": []}),
    ],
)
async def test_a_failed_or_malformed_agent_list_is_an_error(
    response: httpx.Response,
) -> None:
    respx.post(LIST_AGENTS).mock(return_value=response)
    with pytest.raises(HTTPException):
        await list_retell_agents("key_invented")


@respx.mock
async def test_the_connection_test_uses_the_agent_list() -> None:
    route = respx.post(LIST_AGENTS).mock(
        side_effect=[
            httpx.Response(200, json={"items": [], "has_more": False}),
            httpx.Response(401, json={"message": "bad key"}),
            httpx.ConnectError("down"),
        ]
    )
    assert await retell_api.test_retell_connection("key_good") is True
    assert await retell_api.test_retell_connection("key_bad") is False
    assert await retell_api.test_retell_connection("key_any") is False
    assert route.calls[0].request.url.params["limit"] == "1"


@respx.mock
@pytest.mark.parametrize(
    "failure",
    [
        httpx.ReadTimeout("slow"),
        httpx.Response(200, text="not json"),
        httpx.Response(429, json={"message": "rate limited"}),
    ],
)
async def test_when_no_call_can_be_read_the_pull_fails_instead_of_looking_empty(
    failure: object,
) -> None:
    respx.post(LIST_CALLS).mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [_list_item("call_a"), _list_item("call_b")],
                "has_more": False,
            },
        )
    )
    route = respx.get(url__startswith=GET_CALL)
    if isinstance(failure, Exception):
        route.mock(side_effect=failure)
    else:
        route.mock(return_value=failure)
    with pytest.raises(HTTPException) as raised:
        await list_retell_calls("key_invented", agent_id="agent_invented_1")
    assert raised.value.status_code == 502
