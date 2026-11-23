from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.main import app
from app.models.category import SEED as CATEGORY_SEED
from app.models.category import Category
from app.services.n8n import N8nError
from app.services.retell import PLAYGROUND_PACER
from app.services.retell_versions import RetellReadError
from app.tests.utils.user import (
    authentication_token_from_email,
    authentication_token_with_password,
)
from app.tests.utils.utils import AUTH_USER_EMAIL, AUTH_USER_PASSWORD


def _ensure_categories(session: Session) -> None:
    """Seed the categories if missing: the session-end TRUNCATE wipes the migration's
    seed."""
    existing = set(session.execute(text("SELECT key FROM category")).scalars().all())
    for position, (key, name, kind) in enumerate(CATEGORY_SEED, start=1):
        if key not in existing:
            session.add(Category(key=key, name=name, position=position, kind=kind))
    session.commit()


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        _ensure_categories(session)
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


@pytest.fixture(autouse=True)
def _no_provider_version_reads(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Storing a Retell call looks up the agent's version at Retell.

    Tests do not reach Retell: by default the lookup fails the way an unreachable
    provider does, and the call is stored with its version number only. A test that is
    about versions marks itself ``provider_versions`` and supplies its own answers.
    """
    if request.node.get_closest_marker("provider_versions"):
        yield
        return
    with patch(
        "app.services.component_versions.get_retell_agent_at_version",
        AsyncMock(side_effect=RetellReadError("not reachable in tests")),
    ):
        yield


@pytest.fixture(autouse=True)
def _no_playground_pacing() -> Generator[None, None, None]:
    """Requests to Retell's playground are paced to its limit of 8 per 2 seconds.

    Tests answer those requests themselves and make many at once; waiting for the
    limit would only slow them. The pacer has its own test, which turns it back on.
    """
    with patch.object(PLAYGROUND_PACER, "enabled", False):
        yield


@pytest.fixture(autouse=True)
def _no_backend_execution_reads() -> Generator[None, None, None]:
    """Saving a tool mapping, and syncing calls, look for executions in n8n.

    Tests do not reach n8n: by default the lookup fails the way an unreachable backend
    does. A test about executions patches the same function with its own answers.
    """
    with patch(
        "app.services.executions.list_n8n_executions",
        AsyncMock(side_effect=N8nError("not reachable in tests")),
    ):
        yield


@pytest.fixture(autouse=True)
def _simulation_model_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulations run on Connexity's own model key, and a run without it is refused.
    Tests set an invented one, so they never depend on the developer's `.env`; a test
    about the refusal takes it away."""
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "invented-key")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "invented-key")


@pytest.fixture(autouse=True)
def _no_admin_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """With an Anthropic admin key the scheduled call pull also reads Anthropic's cost
    report. Tests never use the developer's `.env` key: a test about the report sets
    an invented one."""
    monkeypatch.setattr(settings, "ANTHROPIC_ADMIN_KEY", None)
