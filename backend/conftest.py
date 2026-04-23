"""Top-level pytest config — runs before any `app.*` import.

Routes local test runs to a dedicated `app_test` database so the test suite's
TRUNCATE teardown can never wipe dev data. CI uses its own throwaway Postgres
container and exports `CI=true`, so we skip the override there.
"""

import os

if not os.environ.get("CI"):
    os.environ["POSTGRES_DB"] = "app_test"

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from app.core.config import settings

    db_uri = str(settings.SQLALCHEMY_DATABASE_URI or "")
    if not db_uri.endswith("/app_test"):
        raise RuntimeError(
            "Test DB safety check failed: expected resolved URI to end with "
            f"'/app_test', got '{db_uri}'. If DATABASE_URL is set in your .env "
            "it overrides POSTGRES_*; unset it for local test runs."
        )

    admin_uri = db_uri.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_uri, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": "app_test"},
        ).scalar()
        if not exists:
            conn.execute(text('CREATE DATABASE "app_test"'))
    admin_engine.dispose()

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
