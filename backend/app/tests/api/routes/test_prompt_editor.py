"""Integration tests for prompt-editor routes including the SSE chat endpoint."""

import json
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import PromptEditorMessageCreate
from app.models.enums import TurnRole
from app.services.llm import LLMStreamChunk, LLMStreamResult, LLMToolCall
from app.tests.utils.eval import (
    create_test_agent,
    create_test_platform_agent,
    create_test_prompt_editor_session,
)

PREFIX = f"{settings.API_V1_STR}/prompt-editor"


# ── Helpers ──────────────────────────────────────────────────────────


def _parse_sse_events(body: str) -> list[dict]:
    """Parse ``event: <type>\\ndata: <json>`` frames from the SSE body."""
    events: list[dict] = []
    for frame in body.split("\n\n"):
        frame = frame.strip()
        if not frame:
            continue
        event_type = None
        data_str = None
        for line in frame.split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data_str = line[6:]
        if event_type and data_str:
            events.append({"type": event_type, "data": json.loads(data_str)})
    return events


def _create_session_via_api(
    client: TestClient,
    cookies: dict[str, str],
    agent_id: uuid.UUID,
) -> dict:
    r = client.post(
        f"{PREFIX}/sessions/",
        json={"agent_id": str(agent_id)},
        cookies=cookies,
    )
    assert r.status_code == 200
    return r.json()


def _llm_stream_factory(
    *,
    chunks: list[LLMStreamChunk],
    final: LLMStreamResult,
):
    async def gen():
        for c in chunks:
            yield c
        yield final

    return gen()


# ── Session CRUD ─────────────────────────────────────────────────────


def test_create_session(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    body = _create_session_via_api(client, superuser_auth_cookies, agent.id)
    assert body["agent_id"] == str(agent.id)
    assert body["status"] == "active"
    assert body["base_prompt"] is not None
    assert body["message_count"] == 0


def test_create_session_non_platform_agent_allowed(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    """Session creation accepts any agent; platform check is on chat only."""
    agent = create_test_agent(db)
    r = client.post(
        f"{PREFIX}/sessions/",
        json={"agent_id": str(agent.id)},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_create_session_agent_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{PREFIX}/sessions/",
        json={"agent_id": str(uuid.uuid4())},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_list_sessions(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    _create_session_via_api(client, superuser_auth_cookies, agent.id)
    r = client.get(f"{PREFIX}/sessions/", cookies=superuser_auth_cookies)
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_list_sessions_filter_by_agent(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    _create_session_via_api(client, superuser_auth_cookies, agent.id)
    r = client.get(
        f"{PREFIX}/sessions/",
        params={"agent_id": str(agent.id)},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    for sess in r.json()["data"]:
        assert sess["agent_id"] == str(agent.id)


def test_get_session(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    created = _create_session_via_api(client, superuser_auth_cookies, agent.id)
    r = client.get(
        f"{PREFIX}/sessions/{created['id']}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_session_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{PREFIX}/sessions/{uuid.uuid4()}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_update_session(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    created = _create_session_via_api(client, superuser_auth_cookies, agent.id)
    r = client.patch(
        f"{PREFIX}/sessions/{created['id']}",
        json={"title": "New title"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "New title"


def test_archive_session(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    created = _create_session_via_api(client, superuser_auth_cookies, agent.id)
    r = client.patch(
        f"{PREFIX}/sessions/{created['id']}",
        json={"status": "archived"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "archived"


def test_delete_session(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    created = _create_session_via_api(client, superuser_auth_cookies, agent.id)
    r = client.delete(
        f"{PREFIX}/sessions/{created['id']}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    # Verify it's gone
    r2 = client.get(
        f"{PREFIX}/sessions/{created['id']}",
        cookies=superuser_auth_cookies,
    )
    assert r2.status_code == 404


# ── Messages ─────────────────────────────────────────────────────────


def test_list_messages(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    user = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert user is not None
    pe_session = create_test_prompt_editor_session(
        db, agent_id=agent.id, created_by=user.id
    )
    crud.create_prompt_editor_message(
        session=db,
        message_in=PromptEditorMessageCreate(
            session_id=pe_session.id, role=TurnRole.USER, content="hi"
        ),
    )
    r = client.get(
        f"{PREFIX}/sessions/{pe_session.id}/messages",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_list_messages_session_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{PREFIX}/sessions/{uuid.uuid4()}/messages",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


# ── SSE Chat Endpoint ────────────────────────────────────────────────


@patch("app.services.prompt_editor.core.call_llm_stream")
def test_chat_happy_path_no_edits(
    mock_stream: object,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    """Chat with no tool calls: reasoning + done (prompt unchanged)."""
    agent = create_test_platform_agent(db, system_prompt="You are helpful.")
    sess = _create_session_via_api(client, superuser_auth_cookies, agent.id)

    final = LLMStreamResult(
        full_content="Looks good already!",
        tool_calls=[],
        usage={"prompt_tokens": 10, "completion_tokens": 5},
        model="gpt-4o-mini",
        latency_ms=100,
        response_cost_usd=0.001,
    )
    mock_stream.return_value = _llm_stream_factory(  # type: ignore[attr-defined]
        chunks=[
            LLMStreamChunk(content="Looks "),
            LLMStreamChunk(content="good already!"),
        ],
        final=final,
    )

    r = client.post(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        json={"content": "Review my prompt", "current_prompt": "You are helpful."},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_events(r.text)
    types = [e["type"] for e in events]

    # Must start with status:analyzing
    assert types[0] == "status"
    assert events[0]["data"]["phase"] == "analyzing"

    # Must contain reasoning events
    assert "reasoning" in types

    # Must end with status:complete then done
    assert types[-2] == "status"
    assert events[-2]["data"]["phase"] == "complete"
    assert types[-1] == "done"

    done_data = events[-1]["data"]
    assert done_data["edited_prompt"] == "You are helpful."
    assert done_data["base_prompt"] == "You are helpful."
    assert done_data["message"]["role"] == "assistant"
    assert done_data["message"]["content"] == "Looks good already!"


@patch("app.services.prompt_editor.core.call_llm_stream")
def test_chat_happy_path_with_edits(
    mock_stream: object,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    """Chat with tool calls: reasoning + edit snapshots + done."""
    agent = create_test_platform_agent(db, system_prompt="Line one\nLine two")
    sess = _create_session_via_api(client, superuser_auth_cookies, agent.id)

    final = LLMStreamResult(
        full_content="Replacing line 2.",
        tool_calls=[
            LLMToolCall(
                id="tc1",
                function_name="edit_prompt",
                arguments={
                    "start_line": 2,
                    "end_line": 2,
                    "new_content": "Better line two",
                },
            )
        ],
        usage={"prompt_tokens": 20, "completion_tokens": 10},
        model="gpt-4o-mini",
        latency_ms=200,
        response_cost_usd=0.002,
    )
    mock_stream.return_value = _llm_stream_factory(  # type: ignore[attr-defined]
        chunks=[LLMStreamChunk(content="Replacing line 2.")],
        final=final,
    )

    r = client.post(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        json={"content": "Fix line 2", "current_prompt": "Line one\nLine two"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200

    events = _parse_sse_events(r.text)
    types = [e["type"] for e in events]

    # Should include editing status and edit events
    assert "edit" in types
    editing_statuses = [
        e
        for e in events
        if e["type"] == "status" and e["data"].get("phase") == "editing"
    ]
    assert len(editing_statuses) >= 1

    # Verify edit event payload
    edit_events = [e for e in events if e["type"] == "edit"]
    assert len(edit_events) == 1
    assert edit_events[0]["data"]["edit_index"] == 0
    assert edit_events[0]["data"]["total_edits"] == 1
    assert "Better line two" in edit_events[0]["data"]["edited_prompt"]

    # Verify done event has updated prompt
    done = next(e for e in events if e["type"] == "done")
    assert done["data"]["edited_prompt"] == "Line one\nBetter line two"


@patch("app.services.prompt_editor.core.call_llm_stream")
def test_chat_multiple_edits(
    mock_stream: object,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    """Multiple tool calls produce multiple edit events."""
    agent = create_test_platform_agent(db, system_prompt="A\nB\nC")
    sess = _create_session_via_api(client, superuser_auth_cookies, agent.id)

    final = LLMStreamResult(
        full_content="Updating.",
        tool_calls=[
            LLMToolCall(
                id="tc1",
                function_name="edit_prompt",
                arguments={"start_line": 1, "end_line": 1, "new_content": "A2"},
            ),
            LLMToolCall(
                id="tc2",
                function_name="edit_prompt",
                arguments={"start_line": 3, "end_line": 3, "new_content": "C2"},
            ),
        ],
        usage={},
        model="gpt-4o-mini",
        latency_ms=50,
        response_cost_usd=None,
    )
    mock_stream.return_value = _llm_stream_factory(chunks=[], final=final)  # type: ignore[attr-defined]

    r = client.post(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        json={"content": "edit both", "current_prompt": "A\nB\nC"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200

    events = _parse_sse_events(r.text)
    edit_events = [e for e in events if e["type"] == "edit"]
    assert len(edit_events) == 2
    assert edit_events[-1]["data"]["total_edits"] == 2

    done = next(e for e in events if e["type"] == "done")
    assert done["data"]["edited_prompt"] == "A2\nB\nC2"


@patch("app.services.prompt_editor.core.call_llm_stream")
def test_chat_persists_messages(
    mock_stream: object,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    """Both user and assistant messages are persisted to the database."""
    agent = create_test_platform_agent(db, system_prompt="Test prompt")
    sess = _create_session_via_api(client, superuser_auth_cookies, agent.id)

    final = LLMStreamResult(
        full_content="Response text.",
        tool_calls=[],
        usage={},
        model="m",
        latency_ms=0,
        response_cost_usd=None,
    )
    mock_stream.return_value = _llm_stream_factory(chunks=[], final=final)  # type: ignore[attr-defined]

    r = client.post(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        json={"content": "Hello there", "current_prompt": "Test prompt"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200

    # Verify messages were persisted
    msgs_r = client.get(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        cookies=superuser_auth_cookies,
    )
    assert msgs_r.status_code == 200
    msgs = msgs_r.json()
    assert msgs["count"] == 2
    roles = [m["role"] for m in msgs["data"]]
    assert "user" in roles
    assert "assistant" in roles
    user_msg = next(m for m in msgs["data"] if m["role"] == "user")
    assert user_msg["content"] == "Hello there"


@patch("app.services.prompt_editor.core.call_llm_stream")
def test_chat_updates_session_edited_prompt(
    mock_stream: object,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    """After edits, the session's edited_prompt is updated."""
    agent = create_test_platform_agent(db, system_prompt="Original")
    sess = _create_session_via_api(client, superuser_auth_cookies, agent.id)

    final = LLMStreamResult(
        full_content="Edited.",
        tool_calls=[
            LLMToolCall(
                id="tc1",
                function_name="edit_prompt",
                arguments={"start_line": 1, "end_line": 1, "new_content": "Updated"},
            )
        ],
        usage={},
        model="m",
        latency_ms=0,
        response_cost_usd=None,
    )
    mock_stream.return_value = _llm_stream_factory(chunks=[], final=final)  # type: ignore[attr-defined]

    r = client.post(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        json={"content": "update", "current_prompt": "Original"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200

    # Check session reflects the edit
    sess_r = client.get(
        f"{PREFIX}/sessions/{sess['id']}",
        cookies=superuser_auth_cookies,
    )
    assert sess_r.status_code == 200
    assert sess_r.json()["edited_prompt"] == "Updated"


def test_chat_session_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{PREFIX}/sessions/{uuid.uuid4()}/messages",
        json={"content": "hi", "current_prompt": "p"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_chat_archived_session(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_platform_agent(db)
    sess = _create_session_via_api(client, superuser_auth_cookies, agent.id)
    # Archive the session
    client.patch(
        f"{PREFIX}/sessions/{sess['id']}",
        json={"status": "archived"},
        cookies=superuser_auth_cookies,
    )

    r = client.post(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        json={"content": "hi", "current_prompt": "p"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 400
    assert "archived" in r.json()["detail"].lower()


def test_chat_non_platform_agent_rejected(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    """Chat endpoint rejects non-platform agents."""
    agent = create_test_agent(db)
    sess = _create_session_via_api(client, superuser_auth_cookies, agent.id)
    r = client.post(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        json={"content": "hi", "current_prompt": "p"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


@patch("app.services.prompt_editor.core.call_llm_stream")
def test_chat_llm_error_yields_error_event(
    mock_stream: object,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    """LLM failure produces an error SSE event."""
    agent = create_test_platform_agent(db, system_prompt="p")
    sess = _create_session_via_api(client, superuser_auth_cookies, agent.id)

    async def boom():
        raise RuntimeError("rate limited")
        yield LLMStreamChunk(content="x")  # pragma: no cover

    mock_stream.return_value = boom()  # type: ignore[attr-defined]

    r = client.post(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        json={"content": "do something", "current_prompt": "p"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200  # SSE always returns 200, errors in stream
    assert r.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_events(r.text)
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) >= 1
    assert "rate limited" in error_events[0]["data"]["detail"]
    # No done event on error
    assert all(e["type"] != "done" for e in events)


@patch("app.services.prompt_editor.core.call_llm_stream")
def test_chat_invalid_edit_lines_dropped(
    mock_stream: object,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    """Out-of-range edit tool calls are dropped; valid ones applied."""
    agent = create_test_platform_agent(db, system_prompt="Single line")
    sess = _create_session_via_api(client, superuser_auth_cookies, agent.id)

    final = LLMStreamResult(
        full_content="Trying edits.",
        tool_calls=[
            LLMToolCall(
                id="bad",
                function_name="edit_prompt",
                arguments={"start_line": 99, "end_line": 99, "new_content": "nope"},
            ),
            LLMToolCall(
                id="good",
                function_name="edit_prompt",
                arguments={"start_line": 1, "end_line": 1, "new_content": "Fixed line"},
            ),
        ],
        usage={},
        model="m",
        latency_ms=0,
        response_cost_usd=None,
    )
    mock_stream.return_value = _llm_stream_factory(chunks=[], final=final)  # type: ignore[attr-defined]

    r = client.post(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        json={"content": "fix", "current_prompt": "Single line"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200

    events = _parse_sse_events(r.text)
    edit_events = [e for e in events if e["type"] == "edit"]
    assert len(edit_events) == 1
    done = next(e for e in events if e["type"] == "done")
    assert done["data"]["edited_prompt"] == "Fixed line"


@patch("app.services.prompt_editor.core.call_llm_stream")
def test_chat_tool_calls_reflected_in_edits(
    mock_stream: object,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    """Tool calls produce edit events and update the prompt."""
    agent = create_test_platform_agent(db, system_prompt="X")
    sess = _create_session_via_api(client, superuser_auth_cookies, agent.id)

    final = LLMStreamResult(
        full_content="Done.",
        tool_calls=[
            LLMToolCall(
                id="tc1",
                function_name="edit_prompt",
                arguments={"start_line": 1, "end_line": 1, "new_content": "Y"},
            )
        ],
        usage={},
        model="m",
        latency_ms=0,
        response_cost_usd=None,
    )
    mock_stream.return_value = _llm_stream_factory(chunks=[], final=final)  # type: ignore[attr-defined]

    r = client.post(
        f"{PREFIX}/sessions/{sess['id']}/messages",
        json={"content": "go", "current_prompt": "X"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200

    events = _parse_sse_events(r.text)

    # Edit event carries the updated prompt
    edit_events = [e for e in events if e["type"] == "edit"]
    assert len(edit_events) == 1
    assert edit_events[0]["data"]["edited_prompt"] == "Y"

    # Done event confirms final state
    done = next(e for e in events if e["type"] == "done")
    assert done["data"]["edited_prompt"] == "Y"
    assert done["data"]["message"]["content"] == "Done."


# ── Presets ──────────────────────────────────────────────────────────


def test_get_presets(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(f"{PREFIX}/presets", cookies=superuser_auth_cookies)
    assert r.status_code == 200
    presets = r.json()
    assert len(presets) == 6
    ids = {p["id"] for p in presets}
    assert "improve_prompt" in ids
    assert "suggest_from_evals" in ids


def test_get_presets_with_agent_id(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    """agent_id param is accepted but currently ignored."""
    agent = create_test_platform_agent(db)
    r = client.get(
        f"{PREFIX}/presets",
        params={"agent_id": str(agent.id)},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert len(r.json()) == 6


# ── Auth ─────────────────────────────────────────────────────────────


def test_unauthenticated_request_rejected(client: TestClient) -> None:
    r = client.get(f"{PREFIX}/sessions/")
    assert r.status_code in (401, 403)
