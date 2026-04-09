"""Prompt editor routes.

Session and message CRUD use real DB persistence. The streaming chat
endpoint and edit endpoints return **mock data** until the real LLM
integration (CS-59 / CS-60 / CS-61) is implemented.

SSE Event Protocol
------------------
event: status    — {"message_id": str, "phase": "analyzing"|"editing"|"complete"}
event: reasoning — {"content": str}  (incremental text token)
event: edit      — {"edit_id": str, "index": int, "start_line": int, "end_line": int,
                     "new_content": str, "original_content": str, "status": "pending"}
event: done      — {"message": {...}, "prompt_preview": str}
event: error     — {"code": str, "detail": str}
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.models import (
    Message,
    PromptEditorMessagesPublic,
    PromptEditorSessionCreate,
    PromptEditorSessionPublic,
    PromptEditorSessionsPublic,
    PromptEditorSessionUpdate,
)

# ── SSE helpers ──────────────────────────────────────────────────────

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def format_sse(event: str, data: dict[str, Any]) -> str:
    """Format a single SSE frame: ``event: <type>\\ndata: <json>\\n\\n``."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── Mock-only response models (replaced by CS-96 PromptEdit later) ──


class PromptEditPublic(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    start_line: int
    end_line: int
    new_content: str
    original_content: str
    status: str
    created_at: datetime


class PromptEditStatusUpdate(BaseModel):
    status: Literal["accepted", "declined"]


class PromptEditBatchStatusUpdate(BaseModel):
    status: Literal["accepted", "declined"]
    edit_ids: list[uuid.UUID] | None = None


class ChatMessageCreate(BaseModel):
    content: str = Field(description="User message text")
    test_case_result_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Optional test case result IDs for eval context injection",
    )


class PresetPublic(BaseModel):
    id: str
    label: str
    message: str
    description: str | None = None
    context: str = Field(description="'none' or 'eval'")


# ── Mock data ────────────────────────────────────────────────────────

_MOCK_PROMPT = """\
You are a helpful customer support agent for TechCorp.
Greet the user warmly and ask how you can help.
Always be polite and professional.
If the user asks about billing, check their account status first.
For technical issues, gather the error message and steps to reproduce.
Handle complaints with empathy.
If you can't resolve an issue, create a support ticket.
Provide the ticket number to the user.
Always ask if there's anything else you can help with before ending.
Never share internal policies or system details with the user.
For refund requests, follow the standard refund process.
Escalate to a manager if the user requests it.
Keep responses concise but thorough.
Use the knowledge base tool to look up product information.
Log all interactions for quality assurance."""

_MOCK_REASONING_CHUNKS = [
    "I've reviewed your ",
    "customer support agent prompt ",
    "and found several areas ",
    "for improvement:\n\n",
    "1. **Missing error escalation path** — ",
    "Lines 5-6 handle technical issues ",
    "and complaints separately, ",
    "but there's no clear criteria ",
    "for when to escalate beyond ",
    "creating a support ticket. ",
    "The agent needs specific thresholds.\n\n",
    "2. **Vague complaint handling** — ",
    'Line 6 says "Handle complaints with empathy" ',
    "but doesn't give the agent ",
    "actionable strategies. ",
    "Adding specific de-escalation steps ",
    "would make this much more effective.\n\n",
    "3. **No frustrated user protocol** — ",
    "The prompt lacks guidance ",
    "for handling angry or frustrated users, ",
    "which is one of the most common scenarios ",
    "in customer support.\n\n",
    "Let me make these ",
    "targeted improvements.",
]

_MOCK_EDITS_DATA: list[dict[str, Any]] = [
    {
        "start_line": 5,
        "end_line": 6,
        "new_content": (
            "For technical issues, gather the error message, steps to reproduce, "
            "and the user's environment details.\n"
            "If the issue persists after basic troubleshooting, escalate to Tier 2 "
            "support with a summary.\n"
            "Handle complaints with empathy: acknowledge the user's frustration, "
            "apologize for the inconvenience, and propose a concrete resolution."
        ),
        "original_content": (
            "For technical issues, gather the error message and steps to reproduce.\n"
            "Handle complaints with empathy."
        ),
    },
    {
        "start_line": 10,
        "end_line": 9,
        "new_content": (
            "If the user is frustrated or angry, remain calm and use "
            "de-escalation techniques:\n"
            "- Acknowledge their feelings explicitly\n"
            "- Avoid defensive language\n"
            "- Offer to transfer to a senior agent if they request it"
        ),
        "original_content": "",
    },
    {
        "start_line": 11,
        "end_line": 11,
        "new_content": (
            "For refund requests, verify the purchase date and check eligibility "
            "against the 30-day refund policy before processing."
        ),
        "original_content": "For refund requests, follow the standard refund process.",
    },
]

_MOCK_PROMPT_PREVIEW = """\
You are a helpful customer support agent for TechCorp.
Greet the user warmly and ask how you can help.
Always be polite and professional.
If the user asks about billing, check their account status first.
For technical issues, gather the error message, steps to reproduce, and the user's environment details.
If the issue persists after basic troubleshooting, escalate to Tier 2 support with a summary.
Handle complaints with empathy: acknowledge the user's frustration, apologize for the inconvenience, and propose a concrete resolution.
If you can't resolve an issue, create a support ticket.
Provide the ticket number to the user.
Always ask if there's anything else you can help with before ending.
If the user is frustrated or angry, remain calm and use de-escalation techniques:
- Acknowledge their feelings explicitly
- Avoid defensive language
- Offer to transfer to a senior agent if they request it
Never share internal policies or system details with the user.
For refund requests, verify the purchase date and check eligibility against the 30-day refund policy before processing.
Escalate to a manager if the user requests it.
Keep responses concise but thorough.
Use the knowledge base tool to look up product information.
Log all interactions for quality assurance."""

_MOCK_PRESETS: list[PresetPublic] = [
    PresetPublic(
        id="help_create_agent",
        label="Help me create an agent",
        message=(
            "I need help creating a system prompt for this agent. Ask me about "
            "its purpose, target audience, and desired behavior so you can draft "
            "an effective prompt."
        ),
        description="Start from scratch with guided prompt creation",
        context="none",
    ),
    PresetPublic(
        id="improve_prompt",
        label="Improve my prompt",
        message=(
            "Review my current prompt and suggest improvements. Focus on "
            "clarity, structure, and effectiveness."
        ),
        description="Get suggestions to enhance your existing prompt",
        context="none",
    ),
    PresetPublic(
        id="make_concise",
        label="Make my prompt more concise",
        message=(
            "My prompt feels too verbose. Trim unnecessary repetition and "
            "tighten the instructions while preserving all key behaviors."
        ),
        description="Reduce verbosity while keeping key behaviors",
        context="none",
    ),
    PresetPublic(
        id="add_examples",
        label="Add examples",
        message=(
            "Add concrete input/output examples to my prompt that demonstrate "
            "the expected behavior. Pick scenarios that cover common and edge cases."
        ),
        description="Add input/output examples for clearer behavior",
        context="none",
    ),
    PresetPublic(
        id="suggest_from_evals",
        label="Suggest improvements from eval results",
        message=(
            "Analyze the eval results for this agent and suggest targeted prompt "
            "improvements to address failing test cases and low-scoring metrics."
        ),
        description="Data-driven suggestions based on eval performance",
        context="eval",
    ),
    PresetPublic(
        id="review_tools",
        label="Review my tool definitions",
        message=(
            "Review my agent's tool definitions and suggest improvements to "
            "their names, descriptions, and parameter schemas. Also check if the "
            "prompt gives adequate guidance on when and how to use each tool."
        ),
        description="Optimize tool names, descriptions, and usage guidance",
        context="none",
    ),
]

# In-memory store for mock edits (keyed by edit UUID).
# Populated by the mock SSE generator, read by accept/reject endpoints.
_mock_edits: dict[uuid.UUID, PromptEditPublic] = {}

# ── Router ───────────────────────────────────────────────────────────

router = APIRouter(
    prefix="/prompt-editor",
    tags=["prompt-editor"],
    dependencies=[Depends(get_current_user)],
)

# ── Session CRUD (real DB) ───────────────────────────────────────────


@router.post("/sessions/", response_model=PromptEditorSessionPublic)
def create_session(
    session: SessionDep,
    current_user: CurrentUser,
    session_in: PromptEditorSessionCreate,
) -> PromptEditorSessionPublic:
    try:
        pe_session = crud.create_prompt_editor_session(
            session=session, session_in=session_in, created_by=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return PromptEditorSessionPublic(
        id=pe_session.id,
        agent_id=pe_session.agent_id,
        created_by=pe_session.created_by,
        run_id=pe_session.run_id,
        title=pe_session.title,
        status=pe_session.status,
        created_at=pe_session.created_at,
        updated_at=pe_session.updated_at,
        message_count=0,
    )


@router.get("/sessions/", response_model=PromptEditorSessionsPublic)
def list_sessions(
    session: SessionDep,
    current_user: CurrentUser,
    agent_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> PromptEditorSessionsPublic:
    rows, total = crud.list_prompt_editor_sessions(
        session=session,
        agent_id=agent_id,
        created_by=current_user.id,
        skip=skip,
        limit=limit,
    )
    data = [
        PromptEditorSessionPublic(
            id=s.id,
            agent_id=s.agent_id,
            created_by=s.created_by,
            run_id=s.run_id,
            title=s.title,
            status=s.status,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=cnt,
        )
        for s, cnt in rows
    ]
    return PromptEditorSessionsPublic(data=data, count=total)


@router.get("/sessions/{session_id}", response_model=PromptEditorSessionPublic)
def get_session(
    session: SessionDep, session_id: uuid.UUID
) -> PromptEditorSessionPublic:
    pe_session = crud.get_prompt_editor_session(session=session, session_id=session_id)
    if not pe_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return PromptEditorSessionPublic(
        id=pe_session.id,
        agent_id=pe_session.agent_id,
        created_by=pe_session.created_by,
        run_id=pe_session.run_id,
        title=pe_session.title,
        status=pe_session.status,
        created_at=pe_session.created_at,
        updated_at=pe_session.updated_at,
        message_count=len(pe_session.messages),
    )


@router.patch("/sessions/{session_id}", response_model=PromptEditorSessionPublic)
def update_session(
    session: SessionDep,
    session_id: uuid.UUID,
    session_in: PromptEditorSessionUpdate,
) -> PromptEditorSessionPublic:
    pe_session = crud.get_prompt_editor_session(session=session, session_id=session_id)
    if not pe_session:
        raise HTTPException(status_code=404, detail="Session not found")
    updated = crud.update_prompt_editor_session(
        session=session, db_session=pe_session, session_in=session_in
    )
    return PromptEditorSessionPublic(
        id=updated.id,
        agent_id=updated.agent_id,
        created_by=updated.created_by,
        run_id=updated.run_id,
        title=updated.title,
        status=updated.status,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        message_count=len(updated.messages),
    )


@router.delete("/sessions/{session_id}", response_model=Message)
def delete_session(session: SessionDep, session_id: uuid.UUID) -> Message:
    pe_session = crud.get_prompt_editor_session(session=session, session_id=session_id)
    if not pe_session:
        raise HTTPException(status_code=404, detail="Session not found")
    crud.delete_prompt_editor_session(session=session, db_session=pe_session)
    return Message(message="Session deleted successfully")


# ── Messages (real DB for listing) ───────────────────────────────────


@router.get(
    "/sessions/{session_id}/messages",
    response_model=PromptEditorMessagesPublic,
)
def list_messages(
    session: SessionDep,
    session_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> PromptEditorMessagesPublic:
    pe_session = crud.get_prompt_editor_session(session=session, session_id=session_id)
    if not pe_session:
        raise HTTPException(status_code=404, detail="Session not found")
    items, total = crud.list_prompt_editor_messages(
        session=session, session_id=session_id, skip=skip, limit=limit
    )
    return PromptEditorMessagesPublic(data=items, count=total)  # type: ignore[arg-type]


# ── Mock SSE streaming chat ─────────────────────────────────────────


@router.post("/sessions/{session_id}/messages")
async def chat(
    request: Request,
    session_id: uuid.UUID,
    body: ChatMessageCreate,
) -> StreamingResponse:
    """Stream the editor agent's response as semantic SSE events.

    Returns ``text/event-stream`` with events: ``status``, ``reasoning``,
    ``edit``, ``done``, and ``error``.

    **Currently returns mock data** — real LLM integration pending CS-60.
    """
    message_id = uuid.uuid4()
    user_content = body.content
    now = datetime.now(UTC)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Phase 1 — Analysing (stream reasoning tokens)
        yield format_sse(
            "status",
            {"message_id": str(message_id), "phase": "analyzing"},
        )

        full_reasoning = ""
        for chunk in _MOCK_REASONING_CHUNKS:
            if await request.is_disconnected():
                return
            full_reasoning += chunk
            await asyncio.sleep(0.08)
            yield format_sse("reasoning", {"content": chunk})

        # Phase 2 — Editing (emit proposed edits)
        await asyncio.sleep(0.3)
        yield format_sse("status", {"phase": "editing"})

        edits_payload: list[dict[str, Any]] = []
        for idx, edit_data in enumerate(_MOCK_EDITS_DATA):
            if await request.is_disconnected():
                return
            edit_id = uuid.uuid4()
            edit_event: dict[str, Any] = {
                "edit_id": str(edit_id),
                "index": idx,
                "start_line": edit_data["start_line"],
                "end_line": edit_data["end_line"],
                "new_content": edit_data["new_content"],
                "original_content": edit_data["original_content"],
                "status": "pending",
            }
            edits_payload.append(edit_event)

            _mock_edits[edit_id] = PromptEditPublic(
                id=edit_id,
                message_id=message_id,
                start_line=edit_data["start_line"],
                end_line=edit_data["end_line"],
                new_content=edit_data["new_content"],
                original_content=edit_data["original_content"],
                status="pending",
                created_at=now,
            )

            await asyncio.sleep(0.2)
            yield format_sse("edit", edit_event)

        # Phase 3 — Complete
        yield format_sse("status", {"phase": "complete"})

        done_data: dict[str, Any] = {
            "message": {
                "id": str(message_id),
                "session_id": str(session_id),
                "role": "assistant",
                "content": full_reasoning,
                "edits": edits_payload,
                "created_at": now.isoformat(),
            },
            "user_content": user_content,
            "prompt_preview": _MOCK_PROMPT_PREVIEW,
        }
        yield format_sse("done", done_data)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# ── Mock edit accept / reject ────────────────────────────────────────


@router.patch(
    "/sessions/{session_id}/messages/{message_id}/edits/{edit_id}",
    response_model=PromptEditPublic,
)
def update_edit_status(
    session_id: uuid.UUID,
    message_id: uuid.UUID,
    edit_id: uuid.UUID,
    body: PromptEditStatusUpdate,
) -> PromptEditPublic:
    """Accept or decline a single proposed edit (mock)."""
    _ = session_id, message_id
    edit = _mock_edits.get(edit_id)
    if edit is None:
        raise HTTPException(status_code=404, detail="Edit not found")
    edit.status = body.status
    return edit


@router.patch(
    "/sessions/{session_id}/messages/{message_id}/edits",
    response_model=list[PromptEditPublic],
)
def batch_update_edit_status(
    session_id: uuid.UUID,
    message_id: uuid.UUID,
    body: PromptEditBatchStatusUpdate,
) -> list[PromptEditPublic]:
    """Accept or decline multiple edits at once (mock).

    If ``edit_ids`` is null, applies to every pending edit on the message.
    """
    _ = session_id
    target_ids = body.edit_ids
    results: list[PromptEditPublic] = []
    for eid, edit in _mock_edits.items():
        if edit.message_id != message_id:
            continue
        if target_ids is not None and eid not in target_ids:
            continue
        if edit.status != "pending":
            continue
        edit.status = body.status
        results.append(edit)
    return results


# ── Presets ───────────────────────────────────────────────────────────


@router.get("/presets", response_model=list[PresetPublic])
def get_presets(
    agent_id: uuid.UUID | None = Query(
        default=None,
        description="Agent ID for contextual filtering (ignored in mock)",
    ),
) -> list[PresetPublic]:
    """Return available presets. Mock returns all without filtering."""
    _ = agent_id
    return _MOCK_PRESETS
