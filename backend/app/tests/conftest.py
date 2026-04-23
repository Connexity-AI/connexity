from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.tests.utils.user import authentication_token_from_email
from app.tests.utils.utils import (
    get_superuser_auth_cookies,
)


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        # Wipe every application table so tables without an FK to "user"
        # (agent, eval_config, test_case, ...) don't accumulate orphans
        # across runs. Keep alembic_version so the schema survives.
        table_names = [
            row[0]
            for row in session.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                )
            ).all()
        ]
        if table_names:
            quoted = ", ".join(f'"{name}"' for name in table_names)
            session.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_auth_cookies(client: TestClient) -> dict[str, str]:
    return get_superuser_auth_cookies(client)


@pytest.fixture(scope="module")
def normal_user_auth_cookies(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
