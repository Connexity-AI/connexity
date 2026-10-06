import pytest
from cryptography.fernet import Fernet
from sqlmodel import Session

from app import crud
from app.core import encryption
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


def test_copies_llm_keys_in_local_env(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(encryption.settings, "ENCRYPTION_KEY", key)
    encryption._fernet.cache_clear()
    app_settings = _settings(
        FIRST_SUPERUSER=random_email(),
        FIRST_SUPERUSER_PASSWORD="secret123",
        ENVIRONMENT="local",
        ENCRYPTION_KEY=key,
        OPENAI_API_KEY="sk-test-1234567890",
    )

    user = init_first_superuser(session=db, app_settings=app_settings)
    assert user is not None
    company = crud.get_company(session=db, company_id=user.company_id)
    assert company is not None
    assert crud.company_has_any_llm_key(company=company)
    encryption._fernet.cache_clear()


def test_does_not_copy_llm_keys_outside_local(db: Session) -> None:
    app_settings = _settings(
        FIRST_SUPERUSER=random_email(),
        FIRST_SUPERUSER_PASSWORD="secret123",
        ENVIRONMENT="staging",
        OPENAI_API_KEY="sk-test-1234567890",
    )

    user = init_first_superuser(session=db, app_settings=app_settings)
    assert user is not None
    company = crud.get_company(session=db, company_id=user.company_id)
    assert company is not None
    assert not crud.company_has_any_llm_key(company=company)
