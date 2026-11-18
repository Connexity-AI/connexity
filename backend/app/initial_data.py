"""Seed a default login so local databases don't need a manual signup.

Runs from ``scripts/prestart.sh`` after migrations. Idempotent: does nothing
unless ``FIRST_SUPERUSER`` / ``FIRST_SUPERUSER_PASSWORD`` are set, and never
touches an existing user.
"""

import logging

from pydantic import ValidationError
from sqlmodel import Session

from app import crud
from app.core.config import Settings, settings
from app.core.db import engine
from app.models import User, UserCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_first_superuser(*, session: Session, app_settings: Settings) -> User | None:
    """Create the ``FIRST_SUPERUSER`` account if configured and missing.

    Returns:
        The created user, or None when seeding is disabled or the user exists.
    """
    email = app_settings.FIRST_SUPERUSER
    password = app_settings.FIRST_SUPERUSER_PASSWORD
    if not email or not password:
        logger.info("FIRST_SUPERUSER not configured; skipping seed")
        return None
    if crud.get_user_by_email(session=session, email=email):
        logger.info(f"User {email} already exists; skipping seed")
        return None

    try:
        user_create = UserCreate(email=email, password=password, full_name="Admin")
    except ValidationError as exc:
        # Runs from prestart.sh: a bad seed value must not stop the backend booting.
        reasons = "; ".join(error["msg"] for error in exc.errors())
        logger.error(f"FIRST_SUPERUSER is invalid; skipping seed: {reasons}")
        return None

    user = crud.create_user(session=session, user_create=user_create)
    logger.info(f"Created user {email}")

    return user


def main() -> None:
    with Session(engine) as session:
        init_first_superuser(session=session, app_settings=settings)


if __name__ == "__main__":
    main()
