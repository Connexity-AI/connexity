"""The read-only n8n client. Every response here is invented."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from app.services import outbound_url
from app.services.n8n import (
    N8nConnectionProblem,
    N8nError,
    check_n8n_connection,
    get_n8n_execution,
    get_n8n_workflow,
    list_n8n_executions,
    list_n8n_workflows,
    n8n_api_root,
)

BASE = "https://n8n.example.com"
# Requests are sent to the address the host was checked to resolve to.
PINNED = "https://93.184.216.34"
EXECUTIONS = f"{PINNED}/api/v1/executions"


@pytest.fixture(autouse=True)
def _public_host() -> object:
    with patch.object(
        outbound_url, "_resolve", AsyncMock(return_value=["93.184.216.34"])
    ) as resolve:
        yield resolve


def test_api_root_accepts_either_form_of_the_address() -> None:
    assert n8n_api_root(BASE) == f"{BASE}/api/v1"
    assert n8n_api_root(f"{BASE}/") == f"{BASE}/api/v1"
    assert n8n_api_root(f"{BASE}/api/v1") == f"{BASE}/api/v1"


@respx.mock
async def test_connection_ok_sends_the_key_and_reads_one_execution() -> None:
    route = respx.get(EXECUTIONS).mock(
        return_value=httpx.Response(200, json={"data": [], "nextCursor": None})
    )
    result = await check_n8n_connection(f"{BASE}/", "key_invented")
    assert result.ok is True
    assert result.base_url == BASE
    request = route.calls.last.request
    assert request.headers["X-N8N-API-KEY"] == "key_invented"
    # Sent to the checked address, presenting the real host name.
    assert request.url.host == "93.184.216.34"
    assert request.headers["Host"] == "n8n.example.com"
    assert request.extensions["sni_hostname"] == "n8n.example.com"
    assert request.url.params["limit"] == "1"


@respx.mock
@pytest.mark.parametrize("status", [401, 403])
async def test_a_refused_key(status: int) -> None:
    respx.get(EXECUTIONS).mock(return_value=httpx.Response(status, json={}))
    result = await check_n8n_connection(BASE, "key_wrong")
    assert (result.ok, result.problem) == (False, N8nConnectionProblem.WRONG_KEY)


@respx.mock
@pytest.mark.parametrize(
    "error", [httpx.ConnectTimeout("slow"), httpx.ConnectError("down")]
)
async def test_unreachable(error: Exception) -> None:
    respx.get(EXECUTIONS).mock(side_effect=error)
    result = await check_n8n_connection(BASE, "key_invented")
    assert (result.ok, result.problem) == (False, N8nConnectionProblem.UNREACHABLE)


@respx.mock
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404, text="Not Found"),
        httpx.Response(200, text="<html>some other site</html>"),
        httpx.Response(200, text=""),
        httpx.Response(200, json={"unexpected": True}),
        httpx.Response(200, json=[]),
        httpx.Response(302, headers={"location": "http://169.254.169.254/"}),
        httpx.Response(500, text="boom"),
    ],
)
async def test_an_address_that_is_not_an_n8n_api(response: httpx.Response) -> None:
    route = respx.get(EXECUTIONS).mock(return_value=response)
    result = await check_n8n_connection(BASE, "key_invented")
    assert (result.ok, result.problem) == (False, N8nConnectionProblem.NOT_N8N)
    # A redirect is never followed.
    assert route.call_count == 1


@respx.mock
async def test_a_private_address_is_refused_before_any_request(
    _public_host: AsyncMock,
) -> None:
    _public_host.return_value = ["10.0.0.5"]
    route = respx.get(EXECUTIONS).mock(return_value=httpx.Response(200, json={}))
    result = await check_n8n_connection(BASE, "key_invented")
    assert (result.ok, result.problem) == (
        False,
        N8nConnectionProblem.ADDRESS_NOT_ALLOWED,
    )
    assert route.call_count == 0


@respx.mock
async def test_http_is_refused_before_any_request() -> None:
    route = respx.get(url__regex=r"^http://.*").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    result = await check_n8n_connection("http://n8n.example.com", "key_invented")
    assert result.problem == N8nConnectionProblem.ADDRESS_NOT_ALLOWED
    assert route.call_count == 0


# ── Reading workflows and executions ───────────────────────────────

WORKFLOWS = f"{PINNED}/api/v1/workflows"
AFTER = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
BEFORE = datetime(2026, 6, 1, 12, 5, tzinfo=UTC)


@respx.mock
async def test_list_workflows_follows_pages_and_leaves_out_archived() -> None:
    route = respx.get(WORKFLOWS).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "w2", "name": "zeta", "active": True},
                        {"id": "w9", "name": "old", "isArchived": True},
                    ],
                    "nextCursor": "page2",
                },
            ),
            httpx.Response(200, json={"data": [{"id": "w1", "name": "Alpha"}]}),
        ]
    )
    workflows = await list_n8n_workflows(BASE, "key_invented")
    assert [(w.id, w.name, w.active) for w in workflows] == [
        ("w1", "Alpha", False),
        ("w2", "zeta", True),
    ]
    assert route.calls[1].request.url.params["cursor"] == "page2"


@respx.mock
async def test_get_workflow_and_a_missing_one() -> None:
    respx.get(f"{WORKFLOWS}/w1").mock(
        return_value=httpx.Response(200, json={"id": "w1", "name": "Alpha"})
    )
    respx.get(f"{WORKFLOWS}/nope").mock(return_value=httpx.Response(404, json={}))
    found = await get_n8n_workflow(BASE, "key_invented", "w1")
    assert found is not None and found.name == "Alpha"
    assert await get_n8n_workflow(BASE, "key_invented", "nope") is None


@respx.mock
async def test_list_executions_asks_for_the_workflow_and_the_window() -> None:
    inside = {"id": 11, "workflowId": "w1", "startedAt": "2026-06-01T12:01:00.000Z"}
    route = respx.get(EXECUTIONS).mock(
        return_value=httpx.Response(200, json={"data": [inside], "nextCursor": None})
    )
    found = await list_n8n_executions(
        BASE,
        "key_invented",
        workflow_id="w1",
        started_after=AFTER,
        started_before=BEFORE,
        max_items=500,
    )
    assert [(e.id, e.workflow_id) for e in found] == [("11", "w1")]
    params = route.calls.last.request.url.params
    assert params["workflowId"] == "w1"
    assert params["startedAfter"] == "2026-06-01T12:00:00Z"
    assert params["startedBefore"] == "2026-06-01T12:05:00Z"


@respx.mock
async def test_an_instance_that_ignores_the_time_filter_is_still_bounded() -> None:
    def page(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": n, "startedAt": "2026-05-01T00:00:00.000Z"}
                    for n in range(250)
                ],
                "nextCursor": "more",
            },
        )

    route = respx.get(EXECUTIONS).mock(side_effect=page)
    found = await list_n8n_executions(
        BASE,
        "key_invented",
        workflow_id="w1",
        started_after=AFTER,
        started_before=BEFORE,
        max_items=500,
    )
    # Everything returned is outside the window, and reading stops at the limit.
    assert found == []
    assert route.call_count == 2


@respx.mock
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text="boom"),
        httpx.Response(200, text=""),
        httpx.Response(200, text="<html>"),
        httpx.Response(200, json={"data": "not a list"}),
        httpx.Response(200, json=[]),
    ],
)
async def test_reading_fails_cleanly_on_an_error_empty_or_malformed_answer(
    response: httpx.Response,
) -> None:
    respx.get(EXECUTIONS).mock(return_value=response)
    respx.get(WORKFLOWS).mock(return_value=response)
    respx.get(f"{EXECUTIONS}/5").mock(return_value=response)
    with pytest.raises(N8nError):
        await list_n8n_executions(
            BASE,
            "key_invented",
            workflow_id="w1",
            started_after=AFTER,
            started_before=BEFORE,
            max_items=10,
        )
    with pytest.raises(N8nError):
        await list_n8n_workflows(BASE, "key_invented")
    with pytest.raises(N8nError):
        await get_n8n_execution(BASE, "key_invented", "5")


@respx.mock
async def test_reading_fails_cleanly_on_a_timeout() -> None:
    respx.get(f"{EXECUTIONS}/5").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(N8nError, match="Could not reach"):
        await get_n8n_execution(BASE, "key_invented", "5")


@respx.mock
async def test_reading_refuses_a_private_address(_public_host: AsyncMock) -> None:
    _public_host.return_value = ["192.168.1.5"]
    route = respx.get(f"{EXECUTIONS}/5").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(N8nError, match="private or local"):
        await get_n8n_execution(BASE, "key_invented", "5")
    assert route.call_count == 0


@respx.mock
async def test_get_execution_asks_for_the_node_data() -> None:
    route = respx.get(f"{EXECUTIONS}/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "data": {}})
    )
    assert (await get_n8n_execution(BASE, "key_invented", "5"))["id"] == 5
    assert route.calls.last.request.url.params["includeData"] == "true"


@respx.mock
async def test_an_n8n_that_refuses_the_time_filter_is_read_without_it() -> None:
    inside = {"id": 11, "workflowId": "w1", "startedAt": "2026-06-01T12:01:00.000Z"}
    outside = {"id": 12, "workflowId": "w1", "startedAt": "2026-06-02T09:00:00.000Z"}

    def answer(request: httpx.Request) -> httpx.Response:
        if "startedAfter" in request.url.params:
            return httpx.Response(400, json={"message": "unknown parameter"})
        return httpx.Response(200, json={"data": [outside, inside]})

    route = respx.get(EXECUTIONS).mock(side_effect=answer)
    found = await list_n8n_executions(
        BASE,
        "key_invented",
        workflow_id="w1",
        started_after=AFTER,
        started_before=BEFORE,
        max_items=500,
    )
    assert [e.id for e in found] == ["11"]
    assert route.call_count == 2


@respx.mock
async def test_a_workflow_id_cannot_reach_another_path() -> None:
    route = respx.get(url__startswith=PINNED).mock(
        return_value=httpx.Response(404, json={})
    )
    assert await get_n8n_workflow(BASE, "key_invented", "../executions/5?x=") is None
    assert route.calls.last.request.url.raw_path == (
        b"/api/v1/workflows/..%2Fexecutions%2F5%3Fx%3D"
    )


@respx.mock
async def test_with_private_addresses_allowed_the_request_goes_to_the_host_itself(
    monkeypatch: pytest.MonkeyPatch, _public_host: AsyncMock
) -> None:
    monkeypatch.setattr(outbound_url.settings, "ALLOW_PRIVATE_INTEGRATION_URLS", True)
    route = respx.get("http://localhost:5678/api/v1/executions/5").mock(
        return_value=httpx.Response(200, json={"id": 5})
    )
    assert (await get_n8n_execution("http://localhost:5678", "key_invented", "5"))[
        "id"
    ] == 5
    assert route.call_count == 1
    _public_host.assert_not_awaited()
