import pytest
from sqlmodel import Session

from app import crud
from app.core.config import Settings
from app.initial_data import init_first_superuser
from app.tests.utils.utils import random_email


def _settings(**overrides: object) -> Settings:
    base = Settings()
    return base.model_copy(
        update={
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            **overrides,
        }
    )


def test_skips_when_not_configured(db: Session) -> None:
    app_settings = _settings(FIRST_SUPERUSER=None, FIRST_SUPERUSER_PASSWORD=None)
    assert init_first_superuser(session=db, app_settings=app_settings) is None


def test_creates_user_once(db: Session) -> None:
    email = random_email()
    app_settings = _settings(
        FIRST_SUPERUSER=email, FIRST_SUPERUSER_PASSWORD="secret123"
    )

    user = init_first_superuser(session=db, app_settings=app_settings)
    assert user is not None
    assert crud.authenticate(session=db, email=email, password="secret123") is not None

    assert init_first_superuser(session=db, app_settings=app_settings) is None


@pytest.mark.parametrize("password", ["short", "a" * 64])
def test_skips_when_password_is_invalid(db: Session, password: str) -> None:
    email = random_email()
    app_settings = _settings(FIRST_SUPERUSER=email, FIRST_SUPERUSER_PASSWORD=password)

    assert init_first_superuser(session=db, app_settings=app_settings) is None
    assert crud.get_user_by_email(session=db, email=email) is None
