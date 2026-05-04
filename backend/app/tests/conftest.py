from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.main import app
from app.models.custom_metric import CustomMetric
from app.services.predefined_metrics import PREDEFINED_METRICS
from app.tests.utils.user import (
    authentication_token_from_email,
    authentication_token_with_password,
)
from app.tests.utils.utils import AUTH_USER_EMAIL, AUTH_USER_PASSWORD


def _ensure_predefined_metrics(session: Session) -> None:
    """Seed predefined metrics into the test DB if missing.

    The session-end TRUNCATE cascades through the ``custom_metric.created_by``
    FK and wipes the rows seeded by the migration. Production never hits this
    because nothing TRUNCATEs ``user`` there; but the test suite needs the
    rows present at every session start, so we re-seed from the canonical
    list whenever they're missing.
    """
    existing = (
        session.execute(
            text(
                "SELECT name FROM custom_metric "
                "WHERE is_predefined = TRUE AND deleted_at IS NULL"
            )
        )
        .scalars()
        .all()
    )
    existing_names = set(existing)
    missing = [m for m in PREDEFINED_METRICS if m.name not in existing_names]
    if not missing:
        return
    for definition in missing:
        session.add(
            CustomMetric(
                name=definition.name,
                display_name=definition.display_name,
                description=definition.description,
                tier=definition.tier,
                default_weight=definition.default_weight,
                score_type=definition.score_type,
                rubric=definition.rubric,
                include_in_defaults=definition.include_in_defaults,
                is_predefined=True,
                is_draft=False,
                created_by=None,
            )
        )
    session.commit()


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        _ensure_predefined_metrics(session)
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
def auth_cookies(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_with_password(
        client=client, email=AUTH_USER_EMAIL, password=AUTH_USER_PASSWORD, db=db
    )


@pytest.fixture(scope="module")
def normal_user_auth_cookies(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
