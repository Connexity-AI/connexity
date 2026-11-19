import json
import httpx
import pytest
from connexity_mcp_server.client import ConnexityBackendClient, ConnexityBackendError
from connexity_mcp_server.config import Settings
from connexity_mcp_server.models import (
    AnswerToGive,
    AnswerToRaise,
    QuestionToRaise,
    SpecRuleToWrite,
    FakeToolResult,
    ScenarioToWrite,
)
from connexity_mcp_server.tools import (
    add_agents,
    get_call,
    list_calls,
    list_categories,
    archive_issue,
    answer_clarifications,
    list_clarifications,
    raise_clarifications,
    write_spec,
    mark_critical_rules,
    get_test_runs,
    list_scenarios,
    mark_issue_fixed,
    run_scenarios,
    write_scenario_set,
    write_scenarios,
    list_issues,
    scan_calls,
    connect_voice_platform,
    create_workspace,
    get_next_task,
    list_tasks,
    move_task,
    get_readiness,
    list_agents,
    list_workspaces,
)
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

WORKSPACE_ID = "3f1c9a52-0f5e-4a59-9a0c-2c3c1f0a7b10"
ANSWER = {
    "rules": ["A rule."],
    "next_steps": ["1. Do this."],
    "guide": "connexity://guides/workspaces",
}


def _authenticated():
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="user-oauth-token",
                client_id="claude-client",
                scopes=["mcp:access"],
            )
        )
    )


async def _call(handler, call):
    settings = Settings(connexity_api_url="http://backend:8000/api/v1")
    token = _authenticated()
    try:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            client = ConnexityBackendClient(settings=settings, http_client=http_client)
            return await call(client)
    finally:
        auth_context_var.reset(token)


@pytest.mark.asyncio
async def test_list_workspaces_forwards_the_token_and_keeps_the_answer() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/mcp/workspaces"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        return httpx.Response(
            200,
            json={
                "data": [{"id": WORKSPACE_ID, "name": "acme.com"}],
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(handler, lambda client: list_workspaces(client))

    assert [w.name for w in result.data] == ["acme.com"]
    assert result.rules == ["A rule."]
    assert result.next_steps == ["1. Do this."]
    assert result.guide == "connexity://guides/workspaces"


@pytest.mark.asyncio
async def test_list_agents_sends_workspace_query_cursor_and_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/agents"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        assert dict(request.url.params) == {
            "query": "booking",
            "cursor": "abc",
            "limit": "100",
        }
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "a1",
                        "name": "Car service booking",
                        "platform": "retell",
                        "platform_agent_name": None,
                        "created_at": "2026-11-12T10:00:00Z",
                    }
                ],
                "next_cursor": "next",
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: list_agents(
            client, workspace_id=WORKSPACE_ID, query="booking", cursor="abc", limit=500
        ),
    )

    assert [a.name for a in result.data] == ["Car service booking"]
    assert result.next_cursor == "next"


@pytest.mark.asyncio
async def test_an_error_in_the_standard_shape_reads_as_next_steps() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "detail": {
                    "error": "Workspace not found",
                    "next_steps": ["Call `list_workspaces`."],
                    "guide": "connexity://guides/workspaces",
                }
            },
        )

    with pytest.raises(ConnexityBackendError) as excinfo:
        await _call(handler, lambda client: list_agents(client, workspace_id="other"))

    assert str(excinfo.value) == (
        "Workspace not found. Next steps: 1. Call `list_workspaces`. "
        "Guide: connexity://guides/workspaces"
    )


@pytest.mark.asyncio
async def test_client_requires_authenticated_mcp_user() -> None:
    settings = Settings(connexity_api_url="http://backend:8000/api/v1")

    async with httpx.AsyncClient() as http_client:
        client = ConnexityBackendClient(settings=settings, http_client=http_client)
        with pytest.raises(ConnexityBackendError, match="authenticated MCP user"):
            await client.list_workspaces()


@pytest.mark.asyncio
async def test_an_invalid_argument_names_it_and_points_to_list_workspaces() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "detail": [
                    {
                        "loc": ["path", "workspace_id"],
                        "msg": "Input should be a valid UUID",
                        "type": "uuid_parsing",
                    }
                ]
            },
        )

    with pytest.raises(ConnexityBackendError) as excinfo:
        await _call(
            handler, lambda client: list_agents(client, workspace_id="acme.com")
        )

    message = str(excinfo.value)
    assert message.startswith(
        "Invalid arguments (`workspace_id`: Input should be a valid UUID)."
    )
    assert "list_workspaces" in message


@pytest.mark.asyncio
async def test_create_workspace_posts_the_name() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/mcp/workspaces"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        assert request.content == b'{"name":"Kestrel Plumbing"}'
        return httpx.Response(
            200,
            json={
                "data": {"id": WORKSPACE_ID, "name": "Kestrel Plumbing"},
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler, lambda client: create_workspace(client, name="Kestrel Plumbing")
    )

    assert result.data.name == "Kestrel Plumbing"


@pytest.mark.asyncio
async def test_get_readiness_reads_the_workspace_steps() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/readiness"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        return httpx.Response(
            200,
            json={
                "data": {
                    "steps": [
                        {
                            "key": "assistant",
                            "name": "Assistant connected",
                            "state": "done",
                            "detail": "Claude",
                        }
                    ],
                    "done": 1,
                    "total": 4,
                    "percent": 25,
                    "first_scan_done": False,
                    "mcp_url": None,
                },
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler, lambda client: get_readiness(client, workspace_id=WORKSPACE_ID)
    )

    assert result.data.percent == 25
    assert result.data.steps[0].state == "done"


@pytest.mark.asyncio
async def test_move_task_posts_the_key_and_its_place() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/tasks/move"
        assert json.loads(request.content) == {"key": "spec:a1", "before": "issue:i1"}
        return httpx.Response(
            200,
            json={
                "data": {"tasks": [], "done": [], "sessions": [], "waiting": 0, "total": 0},
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: move_task(
            client, workspace_id=WORKSPACE_ID, key="spec:a1", before="issue:i1"
        ),
    )

    assert result.data.total == 0


@pytest.mark.asyncio
async def test_list_tasks_reads_a_page_of_the_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/tasks"
        assert request.url.params.get("cursor") == "abc"
        assert request.url.params.get("limit") == "10"
        return httpx.Response(
            200,
            json={
                "data": {
                    "tasks": [
                        {
                            "key": "spec:a1",
                            "kind": "spec",
                            "title": "Write the spec for Front desk",
                            "line": "Spec · Front desk",
                            "position": 1,
                            "state": "in_progress",
                            "holder": {
                                "person": "Alex",
                                "assistant": "Claude Code",
                                "session": "Specs",
                                "taken_at": "2026-11-16T10:00:00Z",
                            },
                        }
                    ],
                    "done": [],
                    "sessions": [],
                    "waiting": 1,
                    "total": 4,
                },
                "next_cursor": "def",
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: list_tasks(
            client, workspace_id=WORKSPACE_ID, cursor="abc", limit=10
        ),
    )

    assert result.data.tasks[0].holder is not None
    assert result.data.tasks[0].holder.session == "Specs"
    assert result.next_cursor == "def"


@pytest.mark.asyncio
async def test_get_next_task_reads_the_workspace_task() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/next-task"
        assert request.url.params.get("session") == "Onboarding"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        return httpx.Response(
            200,
            json={
                "data": {
                    "task": {
                        "key": "spec:a1",
                        "kind": "spec",
                        "title": "Write the spec for Front desk",
                        "position": 2,
                        "agent_id": "a1",
                        "agent_name": "Front desk",
                        "facts": ["Spec · no spec yet"],
                        "waiting_for_person": False,
                    },
                    "previous": {"title": "Scan recent calls", "state": "done"},
                    "waiting_for_person": [],
                    "counts": {
                        "to_do": 3,
                        "waiting_for_person": 1,
                        "in_progress_elsewhere": 0,
                    },
                    "readiness_percent": None,
                },
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: get_next_task(
            client, workspace_id=WORKSPACE_ID, session="Onboarding"
        ),
    )

    assert result.data.task is not None and result.data.task.kind == "spec"
    assert result.data.previous is not None and result.data.previous.state == "done"
    assert result.data.counts.to_do == 3


@pytest.mark.asyncio
async def test_connect_voice_platform_posts_the_key_to_the_workspace() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/connections"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        assert request.content == b'{"platform":"retell","api_key":"key_secret"}'
        return httpx.Response(
            200,
            json={
                "data": {
                    "platform": "Retell",
                    "masked_api_key": "key_****cret",
                    "replaced_earlier_key": False,
                    "connected_by": "Ann through Claude Code",
                },
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: connect_voice_platform(
            client, workspace_id=WORKSPACE_ID, platform="retell", api_key="key_secret"
        ),
    )

    assert result.data.platform == "Retell"
    assert "key_secret" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_add_agents_posts_the_platform_ids() -> None:
    from connexity_mcp_server.models import AgentToAdd

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/agents"
        assert request.content == (
            b'{"agents":[{"platform_agent_id":"agent_1"},'
            b'{"platform_agent_id":"agent_2","name":"Front desk"}]}'
        )
        return httpx.Response(
            200,
            json={
                "data": {
                    "added": [
                        {
                            "id": "a1",
                            "name": "Front desk",
                            "platform": "retell",
                            "platform_agent_id": "agent_2",
                            "platform_agent_name": "Reception v2",
                            "created_at": "2026-11-12T10:00:00Z",
                        }
                    ],
                    "already_added": [],
                    "refused": [
                        {"platform_agent_id": "agent_1", "reason": "Not in the account"}
                    ],
                },
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: add_agents(
            client,
            workspace_id=WORKSPACE_ID,
            agents=[
                AgentToAdd(platform_agent_id="agent_1"),
                AgentToAdd(platform_agent_id="agent_2", name="Front desk"),
            ],
        ),
    )

    assert [a.platform_agent_id for a in result.data.added] == ["agent_2"]
    assert result.data.refused[0].platform_agent_id == "agent_1"


@pytest.mark.asyncio
async def test_scan_calls_posts_and_waits_for_a_step() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/scan"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        assert request.extensions["timeout"]["read"] == 180.0
        return httpx.Response(
            200,
            json={
                "data": {
                    "agents": [
                        {
                            "agent_id": "a1",
                            "name": "Front desk",
                            "stored": 40,
                            "total": 120,
                            "finished": False,
                        }
                    ],
                    "stored_this_step": 40,
                    "finished": False,
                    "calls_without_versions": 0,
                },
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler, lambda client: scan_calls(client, workspace_id=WORKSPACE_ID)
    )

    assert result.data.agents[0].stored == 40
    assert result.data.finished is False


@pytest.mark.asyncio
async def test_list_categories_reads_the_fixed_set() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/categories"
        assert request.headers["Authorization"] == "Bearer user-oauth-token"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"key": "booking", "name": "Booking", "position": 3, "kind": "behaviour"}
                ],
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler, lambda client: list_categories(client, workspace_id=WORKSPACE_ID)
    )

    assert result.data[0].name == "Booking"


@pytest.mark.asyncio
async def test_list_issues_sends_the_search_and_filters_and_keeps_how_it_was_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/issues"
        assert dict(request.url.params) == {
            "query": "slot",
            "agent_id": "a1",
            "category": "booking",
            "severity": "critical",
            "status": "reopened",
            "period": "7d",
        }
        return httpx.Response(
            200,
            json={
                "data": {
                    "tiles": {
                        "open": 2,
                        "critical": 1,
                        "reopened": 1,
                        "resolved": 0,
                        "calls_affected": 5,
                        "calls": 78,
                    },
                    "issues": [
                        {
                            "id": "i1",
                            "agent_id": "a1",
                            "agent_name": "Front desk",
                            "title": "Two bookings for one slot: book",
                            "check_type": "booking_duplicated",
                            "key": "book",
                            "category": "booking",
                            "severity": "critical",
                            "found_by": "code_based",
                            "state": "reopened",
                            "calls_affected": 4,
                            "calls_total": 78,
                        }
                    ],
                },
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: list_issues(
            client,
            workspace_id=WORKSPACE_ID,
            query="slot",
            agent_id="a1",
            category="booking",
            severity="critical",
            status="reopened",
            period="7d",
        ),
    )

    assert result.data.tiles.open == 2
    issue = result.data.issues[0]
    assert (issue.found_by, issue.calls_affected, issue.state) == ("code_based", 4, "reopened")


@pytest.mark.asyncio
async def test_list_calls_sends_the_search_and_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/calls"
        assert dict(request.url.params) == {
            "query": "4821",
            "result": "failed",
            "period": "7d",
        }
        return httpx.Response(
            200,
            json={
                "data": {
                    "tiles": {
                        "calls": 1,
                        "failed": 1,
                        "degraded": 0,
                        "clean": 0,
                        "unchecked": 0,
                    },
                    "calls": [
                        {
                            "id": "c1",
                            "started_at": "2026-11-13T09:42:00",
                            "agent_id": "a1",
                            "agent_name": "Front desk",
                            "caller_last_four": "4821",
                            "duration_seconds": 73,
                            "result": "failed",
                            "worst_finding": {
                                "title": "Two bookings for one slot",
                                "key": "schedule_appointment",
                                "category": "Booking",
                                "severity": "critical",
                                "found_by": "code_based",
                            },
                        }
                    ],
                },
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: list_calls(
            client, workspace_id=WORKSPACE_ID, query="4821", result="failed", period="7d"
        ),
    )

    assert result.data.calls[0].caller_last_four == "4821"
    assert result.data.calls[0].worst_finding.found_by == "code_based"


@pytest.mark.asyncio
async def test_get_call_reads_one_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/calls/c1"
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "c1",
                    "agent_id": "a1",
                    "agent_name": "Front desk",
                    "started_at": "2026-11-13T09:42:00",
                    "result": "failed",
                    "has_recording": True,
                    "entries": [
                        {
                            "kind": "tool",
                            "at_seconds": 41.2,
                            "tool": "schedule_appointment",
                            "status": "ok",
                            "arguments": [{"key": "postalCode", "value": "00000"}],
                            "finding_ids": ["f1"],
                        }
                    ],
                    "findings": [
                        {
                            "id": "f1",
                            "at_seconds": 41.2,
                            "text": "Booking with missing or placeholder details",
                            "category": "Booking",
                            "severity": "critical",
                            "found_by": "code_based",
                            "entry_index": 0,
                        }
                    ],
                },
                "next_cursor": None,
                **ANSWER,
            },
        )

    result = await _call(
        handler, lambda client: get_call(client, workspace_id=WORKSPACE_ID, call_id="c1")
    )

    assert result.data.entries[0].tool == "schedule_appointment"
    assert result.data.findings[0].found_by == "code_based"


@pytest.mark.asyncio
async def test_archive_issue_sends_the_reason_and_duration() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == (
            f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/issues/i1/archive"
        )
        assert json.loads(request.content) == {
            "reason": "Known, approved by Dmytro",
            "duration": "forever",
        }
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "i1",
                    "title": "Two bookings for one slot: book",
                    "check_type": "booking_duplicated",
                    "agent_id": "a1",
                    "agent_name": "Front desk",
                    "category": {"value": "booking", "label": "Booking"},
                    "severity": "critical",
                    "found_by": "code_based",
                    "state": "archived",
                    "archive": {
                        "by": "Dmytro",
                        "assistant": "Claude Code",
                        "at": "2026-11-14T10:00:00Z",
                        "duration": "forever",
                        "reason": "Known, approved by Dmytro",
                    },
                    "tiles": {"calls_affected": 4, "calls_total": 78},
                    "chain": {},
                },
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: archive_issue(
            client,
            workspace_id=WORKSPACE_ID,
            issue_id="i1",
            reason="Known, approved by Dmytro",
            duration="forever",
        ),
    )

    assert result.data.archive is not None
    assert result.data.archive.assistant == "Claude Code"


@pytest.mark.asyncio
async def test_list_calls_sends_the_issue() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["issue_id"] == "i1"
        return httpx.Response(
            200,
            json={
                "data": {
                    "tiles": {
                        "calls": 1,
                        "failed": 1,
                        "degraded": 0,
                        "clean": 0,
                        "unchecked": 0,
                    },
                    "calls": [
                        {
                            "id": "c1",
                            "started_at": "2026-11-14T10:00:00Z",
                            "agent_id": "a1",
                            "agent_name": "Front desk",
                            "result": "failed",
                            "moment": {"at_seconds": 121.0, "times": 2},
                            "agent_version": "15",
                            "issue_findings": [
                                {
                                    "event_ids": ["e4"],
                                    "detail": {"empty": ["postalCode"]},
                                    "effect": "fails",
                                    "check_version": 1,
                                }
                            ],
                        }
                    ],
                },
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: list_calls(
            client, workspace_id=WORKSPACE_ID, issue_id="i1", limit=5
        ),
    )

    assert result.data.calls[0].moment is not None
    assert result.data.calls[0].moment.times == 2
    assert result.data.calls[0].agent_version == "15"
    (finding,) = result.data.calls[0].issue_findings or []
    assert (finding.event_ids, finding.detail) == (["e4"], {"empty": ["postalCode"]})


@pytest.mark.asyncio
async def test_write_spec_sends_every_rule_without_empty_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/agents/a1/spec"
        assert json.loads(request.content) == {
            "rules": [
                {
                    "text": "Never book outside opening hours",
                    "category": "booking",
                    "quote": "only book within opening hours",
                },
                {
                    "text": "Never quote a price",
                    "category": "pricing_and_quotes",
                    "quote": "do not discuss prices",
                    "touches": "money",
                    "key": "k1",
                    "critical": True,
                },
            ]
        }
        return httpx.Response(
            200,
            json={
                "data": {
                    "agent_id": "a1",
                    "agent_name": "Front desk",
                    "current_agent_version": "7",
                    "state": "current",
                    "groups": [],
                    "changes": {
                        "rules": 2,
                        "kept": 1,
                        "added": 1,
                        "dropped": 0,
                        "quotes_checked": True,
                    },
                },
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: write_spec(
            client,
            workspace_id=WORKSPACE_ID,
            agent_id="a1",
            rules=[
                SpecRuleToWrite(
                    text="Never book outside opening hours",
                    category="booking",
                    quote="only book within opening hours",
                ),
                SpecRuleToWrite(
                    text="Never quote a price",
                    category="pricing_and_quotes",
                    quote="do not discuss prices",
                    touches="money",
                    key="k1",
                    critical=True,
                ),
            ],
        ),
    )

    assert result.data.changes is not None
    assert result.data.changes.kept == 1


@pytest.mark.asyncio
async def test_mark_critical_rules_sends_both_lists() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert (
            request.url.path
            == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/agents/a1/spec/critical"
        )
        assert json.loads(request.content) == {
            "critical": ["k1"],
            "not_critical": ["k2"],
        }
        return httpx.Response(
            200,
            json={
                "data": {
                    "agent_id": "a1",
                    "agent_name": "Front desk",
                    "current_agent_version": "7",
                    "state": "current",
                    "groups": [
                        {
                            "category": "pricing_and_quotes",
                            "name": "Pricing and quotes",
                            "rules": [
                                {
                                    "key": "k1",
                                    "text": "Never quote a price",
                                    "source": "prompt",
                                    "critical": True,
                                }
                            ],
                        }
                    ],
                    "counts": {
                        "from_prompt": 1,
                        "from_clarifications": 0,
                        "in_conflict": 0,
                        "critical": 1,
                    },
                },
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: mark_critical_rules(
            client,
            workspace_id=WORKSPACE_ID,
            agent_id="a1",
            critical=["k1"],
            not_critical=["k2"],
        ),
    )

    assert result.data.groups[0].rules[0].critical is True
    assert result.data.counts is not None
    assert result.data.counts.critical == 1


_CLARIFICATION = {
    "id": "c1",
    "agent_id": "a1",
    "agent_name": "Front desk",
    "question": "The agent changed an existing appointment on 2 calls. Is it allowed to?",
    "answers": [
        {"letter": "a", "label": "Yes", "rule": "The agent may change appointments"},
        {"letter": "b", "label": "Never", "rule": "Never change an appointment"},
    ],
    "category": "booking",
    "category_name": "Booking",
    "calls_seen": 0,
    "call_ids": [],
    "spec_version": 1,
    "state": "open",
    "raised_by": "dmytro",
    "raised_at": "2026-11-15T12:00:00Z",
}


@pytest.mark.asyncio
async def test_raise_clarifications_sends_questions_without_empty_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert (
            request.url.path
            == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/agents/a1/clarifications"
        )
        assert json.loads(request.content) == {
            "questions": [
                {
                    "question": _CLARIFICATION["question"],
                    "answers": [
                        {"label": "Yes", "rule": "The agent may change appointments"},
                        {"label": "Never", "rule": "Never change an appointment"},
                    ],
                    "category": "booking",
                }
            ]
        }
        return httpx.Response(200, json={"data": [_CLARIFICATION], **ANSWER})

    result = await _call(
        handler,
        lambda client: raise_clarifications(
            client,
            workspace_id=WORKSPACE_ID,
            agent_id="a1",
            questions=[
                QuestionToRaise(
                    question=str(_CLARIFICATION["question"]),
                    answers=[
                        AnswerToRaise(
                            label="Yes", rule="The agent may change appointments"
                        ),
                        AnswerToRaise(label="Never", rule="Never change an appointment"),
                    ],
                    category="booking",
                )
            ],
        ),
    )

    assert result.data[0].answers[1].letter == "b"


@pytest.mark.asyncio
async def test_list_clarifications_passes_only_given_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/clarifications"
        assert dict(request.url.params) == {"agent_id": "a1", "state": "parked"}
        return httpx.Response(
            200,
            json={
                "data": {
                    "counts": {"open": 0, "answered": 0, "parked": 1},
                    "data": [_CLARIFICATION | {"state": "parked"}],
                },
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: list_clarifications(
            client, workspace_id=WORKSPACE_ID, agent_id="a1", state="parked"
        ),
    )

    assert result.data.counts.parked == 1


@pytest.mark.asyncio
async def test_answer_clarifications_sends_each_answer() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert (
            request.url.path
            == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/clarifications/answers"
        )
        assert json.loads(request.content) == {
            "answers": [
                {"clarification_id": "c1", "answer": "b", "proposed": True},
                {"clarification_id": "c2", "answer": "park"},
            ]
        }
        return httpx.Response(
            200,
            json={
                "data": {
                    "answered": 1,
                    "parked": 1,
                    "specs": [
                        {
                            "agent_id": "a1",
                            "agent_name": "Front desk",
                            "spec_version": 2,
                            "rules_added": 1,
                        }
                    ],
                    "open": 0,
                },
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: answer_clarifications(
            client,
            workspace_id=WORKSPACE_ID,
            answers=[
                AnswerToGive(clarification_id="c1", answer="b", proposed=True),
                AnswerToGive(clarification_id="c2", answer="park"),
            ],
        ),
    )

    assert result.data.specs[0].spec_version == 2


_SCENARIO = {
    "id": "s1",
    "name": "Price pushback",
    "caller": "A policyholder renewing",
    "first_turn": "user",
    "fake_tool_results": [
        {"tool": "quote_lookup", "arguments": {"policy": None}, "result": {"price": 420}}
    ],
    "rules": [{"key": "k1", "text": "Never quote above the lookup", "critical": True}],
    "sets": ["smoke"],
    "updated_at": "2026-11-17T10:00:00Z",
}


@pytest.mark.asyncio
async def test_write_scenarios_sends_them_without_empty_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert (
            request.url.path
            == f"/api/v1/mcp/workspaces/{WORKSPACE_ID}/agents/a1/scenarios"
        )
        assert json.loads(request.content) == {
            "scenarios": [
                {
                    "archive": False,
                    "name": "Price pushback",
                    "caller": "A policyholder renewing",
                    "caller_goal": "Renew only if the price did not go up",
                    "agent_variables": {"customer_name": "Sam"},
                    "fake_tool_results": [
                        {"tool": "quote_lookup", "result": {"price": 420}}
                    ],
                    "rules": ["k1"],
                },
                {
                    "id": "s0",
                    "archive": True,
                    "name": "",
                    "fake_tool_results": [],
                    "rules": [],
                },
            ]
        }
        return httpx.Response(
            200, json={"data": {"scenarios": [_SCENARIO], "archived": 1}, **ANSWER}
        )

    result = await _call(
        handler,
        lambda client: write_scenarios(
            client,
            workspace_id=WORKSPACE_ID,
            agent_id="a1",
            scenarios=[
                ScenarioToWrite(
                    name="Price pushback",
                    caller="A policyholder renewing",
                    caller_goal="Renew only if the price did not go up",
                    agent_variables={"customer_name": "Sam"},
                    fake_tool_results=[
                        FakeToolResult(tool="quote_lookup", result={"price": 420})
                    ],
                    rules=["k1"],
                ),
                ScenarioToWrite(id="s0", archive=True),
            ],
        ),
    )

    assert result.data.archived == 1
    assert result.data.scenarios[0].rules[0].critical is True


@pytest.mark.asyncio
async def test_list_scenarios_sends_the_set_as_set() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert dict(request.url.params) == {"rule_key": "k1", "set": "smoke"}
        return httpx.Response(
            200,
            json={
                "data": {
                    "agent_id": "a1",
                    "agent_name": "Front desk",
                    "data": [_SCENARIO],
                    "sets": [{"id": "e1", "name": "smoke", "scenario_ids": ["s1"]}],
                    "counts": {
                        "scenarios": 1,
                        "rules": 3,
                        "rules_listed": 1,
                        "critical_unlisted": 1,
                        "listing_gone_rules": 0,
                    },
                    "unlisted_rules": [{"key": "k2", "text": "x", "critical": True}],
                },
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: list_scenarios(
            client, workspace_id=WORKSPACE_ID, agent_id="a1", rule_key="k1", set_name="smoke"
        ),
    )

    assert result.data.counts.critical_unlisted == 1
    assert result.data.sets[0].scenario_ids == ["s1"]


@pytest.mark.asyncio
async def test_write_scenario_set_and_archiving_answers_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/agents/a1/scenario-sets")
        body = json.loads(request.content)
        if body["scenario_ids"]:
            assert body == {"name": "smoke", "scenario_ids": ["s1"]}
            data = {"id": "e1", "name": "smoke", "scenario_ids": ["s1"]}
        else:
            data = None
        return httpx.Response(200, json={"data": data, **ANSWER})

    made = await _call(
        handler,
        lambda client: write_scenario_set(
            client, workspace_id=WORKSPACE_ID, agent_id="a1", name="smoke", scenario_ids=["s1"]
        ),
    )
    archived = await _call(
        handler,
        lambda client: write_scenario_set(
            client, workspace_id=WORKSPACE_ID, agent_id="a1", name="smoke", scenario_ids=[]
        ),
    )

    assert made.data is not None and made.data.name == "smoke"
    assert archived.data is None


@pytest.mark.asyncio
async def test_run_scenarios_sends_one_scope_and_the_repeats() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/agents/a1/test-runs")
        assert json.loads(request.content) == {
            "all": False,
            "session": "Testing",
            "set": "smoke",
            "repeats": 2,
        }
        return httpx.Response(200, json={"data": {"run_id": "r1", "calls": 6}, **ANSWER})

    result = await _call(
        handler,
        lambda client: run_scenarios(
            client,
            workspace_id=WORKSPACE_ID,
            agent_id="a1",
            set_name="smoke",
            repeats=2,
            session="Testing",
        ),
    )

    assert result.data.run_id == "r1"
    assert result.data.calls == 6


@pytest.mark.asyncio
async def test_get_test_runs_reads_one_run_in_detail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert dict(request.url.params) == {"run_id": "r1", "limit": "10"}
        return httpx.Response(
            200,
            json={
                "data": {
                    "run": {
                        "id": "r1",
                        "status": "completed",
                        "scope": "set",
                        "set_name": "smoke",
                        "repeats": 2,
                        "created_at": "2026-11-17T10:00:00Z",
                        "counts": {"calls": 2, "finished": 2, "rules_failed": 1, "flaky": 1},
                        "rules": [
                            {"key": "k1", "critical": True, "passed": 1, "failed": 1, "flaky": True}
                        ],
                        "calls": [
                            {
                                "id": "c1",
                                "scenario_id": "s1",
                                "scenario_name": "Wants a refund",
                                "repeat": 1,
                                "finished": True,
                                "verdicts": [
                                    {"key": "k1", "outcome": "failed", "reason": "x", "turns": [3]}
                                ],
                                "default_fakes": ["book"],
                            }
                        ],
                    },
                    "runs": [],
                },
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: get_test_runs(
            client, workspace_id=WORKSPACE_ID, agent_id="a1", run_id="r1", limit=10
        ),
    )

    assert result.data.run is not None
    assert result.data.run.rules[0].flaky is True
    assert result.data.run.calls[0].verdicts[0].outcome == "failed"
    assert result.data.run.calls[0].default_fakes == ["book"]



@pytest.mark.asyncio
async def test_get_test_runs_reads_a_versions_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert dict(request.url.params) == {"version": "15"}
        return httpx.Response(
            200,
            json={
                "data": {
                    "results": {
                        "version": "15",
                        "verdict": "partial",
                        "full_run": {
                            "id": "r1",
                            "status": "completed",
                            "scope": "all",
                            "repeats": 3,
                            "created_at": "2026-11-19T10:00:00Z",
                            "full": True,
                            "verdict": "partial",
                            "totals": {
                                "rules": 2,
                                "passed": 1,
                                "did_not_come_up": 1,
                            },
                            "assistant_name": "Claude Code",
                            "session_name": "Testing",
                        },
                        "coverage": {
                            "rules": 2,
                            "covered": 1,
                            "pct": 50,
                            "uncovered": [
                                {
                                    "key": "k2",
                                    "text": "x",
                                    "category": "Booking",
                                    "critical": True,
                                    "why": "no_scenario",
                                }
                            ],
                        },
                        "checks": [
                            {
                                "check_type": "tool_call_failed",
                                "title": "Tool call failed",
                                "found": 2,
                                "critical": True,
                            }
                        ],
                    },
                    "runs": [],
                },
                **ANSWER,
            },
        )

    result = await _call(
        handler,
        lambda client: get_test_runs(
            client, workspace_id=WORKSPACE_ID, agent_id="a1", version="15"
        ),
    )

    assert result.data.results is not None
    assert result.data.results.verdict == "partial"
    full = result.data.results.full_run
    assert full is not None and full.full and full.totals is not None
    assert (full.totals.passed, full.totals.did_not_come_up) == (1, 1)
    assert full.session_name == "Testing"
    assert result.data.results.checks[0].critical is True
    assert result.data.results.coverage is not None
    assert result.data.results.coverage.uncovered[0].why == "no_scenario"


@pytest.mark.asyncio
async def test_mark_issue_fixed_sends_the_version_and_note() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/issues/i1/fixed")
        assert json.loads(request.content) == {"version": "16", "note": "Asked first"}
        return httpx.Response(422, json={"detail": {"error": "x", "next_steps": []}})

    with pytest.raises(ConnexityBackendError):
        await _call(
            handler,
            lambda client: mark_issue_fixed(
                client,
                workspace_id=WORKSPACE_ID,
                issue_id="i1",
                version="16",
                note="Asked first",
            ),
        )
