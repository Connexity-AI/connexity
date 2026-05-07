import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.config import settings
from app.models import Message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

DOCS_URL = "https://github.com/Connexity-AI/connexity/blob/main/README.md"


class MockWebhookResponse(BaseModel):
    message: str
    received_event_type: str | None = None
    payload_received: bool


@router.get("/", response_model=Message)
def health() -> Message:
    required_vars = {
        "SITE_URL": bool(settings.SITE_URL),
        "DATABASE_URL": bool(settings.DATABASE_URL),
        "JWT_SECRET_KEY": bool(settings.JWT_SECRET_KEY),
    }

    message = "All required environment variables are set."

    missing_vars = [name for name, is_set in required_vars.items() if not is_set]

    if missing_vars:
        message = (
            f"Missing required environment variables: {', '.join(missing_vars)}. "
            f"See documentation: {DOCS_URL}"
        )
        logger.error(message)

    return Message(message=message)


@router.post("/mock-webhook", response_model=MockWebhookResponse)
async def mock_webhook(request: Request) -> MockWebhookResponse:
    payload: dict[str, Any] | None = None

    try:
        body = await request.json()
        if isinstance(body, dict):
            payload = body
    except ValueError:
        payload = None

    event_type = None
    if payload is not None:
        candidate = payload.get("event_type")
        if isinstance(candidate, str):
            event_type = candidate

    return MockWebhookResponse(
        message="Mock webhook received payload",
        received_event_type=event_type,
        payload_received=payload is not None,
    )
