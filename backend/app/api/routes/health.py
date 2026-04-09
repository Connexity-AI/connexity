import logging

from fastapi import APIRouter

from app.core.config import settings
from app.models import Message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

DOCS_URL = "https://github.com/space-step/connexity-evals/blob/main/README.md"


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
