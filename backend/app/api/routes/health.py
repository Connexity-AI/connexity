import logging

from fastapi import APIRouter

from app.core.config import settings
from app.models import Message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

DOCS_URL = "https://github.com/space-step/connexity-evals/blob/main/README.md"


@router.get("/", response_model=Message)
def health():
    required_vars = {
        "SITE_URL": settings.SITE_URL,
        "DATABASE_URL": settings.DATABASE_URL,
        "JWT_SECRET_KEY": settings.JWT_SECRET_KEY,
        "SESSION_SECRET_KEY": settings.SESSION_SECRET_KEY,
    }

    message = "All required environment variables are set."

    missing_vars = [name for name, value in required_vars.items() if not value]

    if missing_vars:
        message = (
            f"Missing required environment variables: {', '.join(missing_vars)}. "
            f"See documentation: {DOCS_URL}"
        )
        logger.error(message)

    return Message(message=message)
