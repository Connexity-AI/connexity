"""Prompt editor routes — sessions, messages, and SSE chat with the editor LLM."""

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from app import crud
from app.api.deps import CurrentCompany, CurrentUser, SessionDep, get_current_user
from app.core.config import settings
from app.core.db import engine
from app.models import (
    Message,
    PromptEditorChatMessageCreate,
    PromptEditorMessageCreate,
    PromptEditorMessagePublic,
    PromptEditorMessagesPublic,
    PromptEditorSessionBasePromptUpdate,
    PromptEditorSessionCreate,
    PromptEditorSessionPublic,
    PromptEditorSessionsPublic,
    PromptEditorSessionUpdate,
)
from app.models.enums import PromptEditorSessionStatus, TurnRole
from app.services.prompt_editor import (
    EditorInput,
    EditorResult,
    Preset,
    PromptEditor,
    build_eval_context,
    format_eval_context_for_prompt,
    get_available_presets,
    platform_agent_required,
)

logger = logging.getLogger(__name__)

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def format_sse(event: str, data: dict[str, Any]) -> str:
    """Format a single SSE frame: ``event: <type>\\ndata: <json>\\n\\n``."""
    return f"event: {event}\ndata: {json.dumps(jsonable_encoder(data))}\n\n"


class PresetPublic(BaseModel):
    """API shape for a preset (excludes internal ``requires`` gates)."""

    id: str
    label: str
    message: str
    description: str | None = None
    context: str = Field(description="'none' or 'eval'")


def _preset_to_public(preset: Preset) -> PresetPublic:
    return PresetPublic(
        id=preset.id,
        label=preset.label,
        message=preset.message,
        description=preset.description,
        context=preset.context.value,
    )


router = APIRouter(
    prefix="/prompt-editor",
    tags=["prompt-editor"],
    dependencies=[Depends(get_current_user)],
)


def _session_public(pe_session: Any, message_count: int) -> PromptEditorSessionPublic:
    return PromptEditorSessionPublic(
        id=pe_session.id,
        agent_id=pe_session.agent_id,
        created_by=pe_session.created_by,
        run_id=pe_session.run_id,
        title=pe_session.title,
        status=pe_session.status,
        base_prompt=pe_session.base_prompt,
        edited_prompt=pe_session.edited_prompt,
        created_at=pe_session.created_at,
        updated_at=pe_session.updated_at,
        message_count=message_count,
    )


@router.post("/sessions/", response_model=PromptEditorSessionPublic)
def create_session(
    session: SessionDep,
    current_user: CurrentUser,
    company_id: CurrentCompany,
    session_in: PromptEditorSessionCreate,
) -> PromptEditorSessionPublic:
    try:
        pe_session = crud.create_prompt_editor_session(
            session=session,
            session_in=session_in,
            company_id=company_id,
            created_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return _session_public(pe_session, message_count=0)


@router.get("/sessions/", response_model=PromptEditorSessionsPublic)
def list_sessions(
    session: SessionDep,
    current_user: CurrentUser,
    company_id: CurrentCompany,
    agent_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> PromptEditorSessionsPublic:
    rows, total = crud.list_prompt_editor_sessions(
        session=session,
        company_id=company_id,
        agent_id=agent_id,
        created_by=current_user.id,
        skip=skip,
        limit=limit,
    )
    data = [_session_public(s, cnt) for s, cnt in rows]
    return PromptEditorSessionsPublic(data=data, count=total)


@router.get("/sessions/{session_id}", response_model=PromptEditorSessionPublic)
def get_session(
    session: SessionDep, company_id: CurrentCompany, session_id: uuid.UUID
) -> PromptEditorSessionPublic:
    pe_session = crud.get_prompt_editor_session(
        session=session, session_id=session_id, company_id=company_id
    )
    if not pe_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_public(pe_session, message_count=len(pe_session.messages))


@router.patch("/sessions/{session_id}", response_model=PromptEditorSessionPublic)
def update_session(
    session: SessionDep,
    company_id: CurrentCompany,
    session_id: uuid.UUID,
    session_in: PromptEditorSessionUpdate,
) -> PromptEditorSessionPublic:
    pe_session = crud.get_prompt_editor_session(
        session=session, session_id=session_id, company_id=company_id
    )
    if not pe_session:
        raise HTTPException(status_code=404, detail="Session not found")
    updated = crud.update_prompt_editor_session(
        session=session, db_session=pe_session, session_in=session_in
    )
    return _session_public(updated, message_count=len(updated.messages))


@router.patch(
    "/sessions/{session_id}/base-prompt",
    response_model=PromptEditorSessionPublic,
)
def update_session_base_prompt(
    session: SessionDep,
    company_id: CurrentCompany,
    session_id: uuid.UUID,
    body: PromptEditorSessionBasePromptUpdate,
) -> PromptEditorSessionPublic:
    """Set ``base_prompt`` (diff baseline), e.g. after the agent draft is saved."""
    pe_session = crud.get_prompt_editor_session(
        session=session, session_id=session_id, company_id=company_id
    )
    if not pe_session:
        raise HTTPException(status_code=404, detail="Session not found")
    updated = crud.update_prompt_editor_session_base_prompt(
        session=session,
        db_session=pe_session,
        base_prompt=body.base_prompt,
    )
    return _session_public(updated, message_count=len(updated.messages))


@router.delete("/sessions/{session_id}", response_model=Message)
def delete_session(
    session: SessionDep, company_id: CurrentCompany, session_id: uuid.UUID
) -> Message:
    pe_session = crud.get_prompt_editor_session(
        session=session, session_id=session_id, company_id=company_id
    )
    if not pe_session:
        raise HTTPException(status_code=404, detail="Session not found")
    crud.delete_prompt_editor_session(session=session, db_session=pe_session)
    return Message(message="Session deleted successfully")


@router.get(
    "/sessions/{session_id}/messages",
    response_model=PromptEditorMessagesPublic,
)
def list_messages(
    session: SessionDep,
    company_id: CurrentCompany,
    session_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> PromptEditorMessagesPublic:
    pe_session = crud.get_prompt_editor_session(
        session=session, session_id=session_id, company_id=company_id
    )
    if not pe_session:
        raise HTTPException(status_code=404, detail="Session not found")
    items, total = crud.list_prompt_editor_messages(
        session=session,
        session_id=session_id,
        skip=skip,
        limit=limit,
    )
    public_items = [
        PromptEditorMessagePublic.model_validate(m, from_attributes=True) for m in items
    ]
    return PromptEditorMessagesPublic(data=public_items, count=total)


@router.post("/sessions/{session_id}/messages")
async def chat(
    request: Request,
    session: SessionDep,
    company_id: CurrentCompany,
    session_id: uuid.UUID,
    body: PromptEditorChatMessageCreate,
) -> StreamingResponse:
    """Stream the editor agent response (reasoning + full-text edit snapshots).

    The SSE generator outlives the FastAPI dependency scope (``get_db`` closes
    the SQLAlchemy ``Session`` once this function returns the
    ``StreamingResponse``).  Therefore we:

    1. Read all data we need *before* returning and copy it into plain Python
       objects so the generator never touches the original session.
    2. Open a **new** ``Session`` inside the generator for the DB writes that
       happen after the LLM stream completes.
    """
    pe_session = crud.get_prompt_editor_session(
        session=session, session_id=session_id, company_id=company_id
    )
    if not pe_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if pe_session.status != PromptEditorSessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is archived")

    agent = crud.get_agent(
        session=session, agent_id=pe_session.agent_id, company_id=company_id
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        platform_agent_required(agent)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    prior_messages, _ = crud.list_prompt_editor_messages(
        session=session, session_id=session_id, skip=0, limit=500
    )

    eval_ctx = await build_eval_context(
        db_session=session,
        agent=agent,
        run_id=pe_session.run_id,
        test_case_result_ids=body.test_case_result_ids,
    )
    eval_context_str = (
        format_eval_context_for_prompt(eval_ctx) if eval_ctx is not None else None
    )

    # Extract scalar data and detach ORM objects the generator will need
    # BEFORE the commit inside create_prompt_editor_message expires them.
    base_prompt = pe_session.base_prompt or ""
    session.expunge(agent)
    for msg in prior_messages:
        session.expunge(msg)

    try:
        crud.create_prompt_editor_message(
            session=session,
            company_id=company_id,
            message_in=PromptEditorMessageCreate(
                session_id=session_id,
                role=TurnRole.USER,
                content=body.content,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            editor = PromptEditor(
                EditorInput(
                    agent=agent,
                    session_messages=prior_messages,
                    user_message=body.content,
                    current_prompt=body.current_prompt,
                    eval_context=eval_context_str,
                    llm_provider=body.provider,
                    llm_model=body.model,
                )
            )
        except Exception as exc:
            logger.exception("PromptEditor init failed: %s", exc)
            yield format_sse(
                "error", {"detail": f"Failed to build LLM messages: {exc}"}
            )
            return

        result: EditorResult | None = None
        async for ev in editor.run_stream(
            app_settings=settings,
            is_disconnected=request.is_disconnected,
        ):
            if ev.type == "error":
                yield format_sse("error", ev.data)
                return
            if ev.type == "reasoning":
                yield format_sse("reasoning", ev.data)
            elif ev.type == "status":
                yield format_sse("status", ev.data)
            elif ev.type == "edit":
                yield format_sse("edit", ev.data)
            elif ev.type == "done":
                result = ev.data["result"]

        if result is None:
            return

        # Open a fresh DB session for the post-stream writes; the
        # dependency-scoped session is already closed at this point.
        with Session(engine) as db:
            try:
                assistant_msg = crud.create_prompt_editor_message(
                    session=db,
                    company_id=company_id,
                    message_in=PromptEditorMessageCreate(
                        session_id=session_id,
                        role=TurnRole.ASSISTANT,
                        content=result.content,
                        tool_calls=result.tool_calls_payload,
                    ),
                )
            except ValueError as exc:
                logger.warning("Failed to persist assistant message: %s", exc)
                yield format_sse("error", {"detail": str(exc)})
                return

            fresh_pe_session = crud.get_prompt_editor_session(
                session=db, session_id=session_id, company_id=company_id
            )
            if fresh_pe_session is None:
                yield format_sse("error", {"detail": "Session not found after stream"})
                return
            crud.update_prompt_editor_session_edited_prompt(
                session=db,
                db_session=fresh_pe_session,
                edited_prompt=result.edited_prompt,
            )

            yield format_sse("status", {"phase": "complete"})
            message_public = PromptEditorMessagePublic.model_validate(
                assistant_msg, from_attributes=True
            )
            done_payload = {
                "message": message_public.model_dump(mode="json"),
                "edited_prompt": result.edited_prompt,
                "base_prompt": base_prompt,
            }
            yield format_sse("done", done_payload)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/presets", response_model=list[PresetPublic])
def get_presets(
    session: SessionDep,
    company_id: CurrentCompany,
    agent_id: uuid.UUID = Query(description="Agent ID for contextual filtering"),
) -> list[PresetPublic]:
    agent = crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    presets = get_available_presets(agent=agent, session=session)
    return [_preset_to_public(p) for p in presets]
