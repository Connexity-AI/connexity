"""Top-level pytest config — runs before any `app.*` import.

Routes local test runs to a dedicated `app_test` database on the local Postgres
(built from POSTGRES_*, never from DATABASE_URL) so the test suite's TRUNCATE
teardown can never wipe dev data or reach a hosted database. CI uses its own
throwaway Postgres container and exports `CI=true`, so we skip the override there.

Skipped automatically when the requested pytest targets are exclusively under
``cli/tests/`` — those are pure HTTP-mock unit tests and don't need a DB.
"""

import os
import sys


def _needs_app_db() -> bool:
    """True if any requested test path needs the app DB."""
    if os.environ.get("CI"):
        return False  # CI bootstraps the DB itself.
    args = [a for a in sys.argv[1:] if a and not a.startswith("-")]
    if not args:
        return True  # whole-tree discovery — assume app tests are included.
    # Setup is required unless every requested path is a pure CLI test path.
    return not all(
        a.startswith("cli/tests") or a.startswith("./cli/tests") for a in args
    )


_TEST_DB_NAME = "app_test"


def _redact(uri: str) -> str:
    """Host, port and database only: never print credentials."""
    from sqlalchemy.engine import make_url

    url = make_url(uri)
    return f"{url.host}:{url.port}/{url.database}"


def _local_test_database_url() -> str:
    """Resolve the URL of the local test database.

    ``TEST_DATABASE_URL`` wins when set. Otherwise the URL is built from the
    ``POSTGRES_*`` settings (environment first, then the root ``.env``) with the
    database name replaced by ``app_test``. ``DATABASE_URL`` is deliberately not
    consulted, so a ``.env`` that points at a hosted database can never receive
    test traffic.
    """
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit

    from dotenv import dotenv_values

    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    values = {**dotenv_values(env_file), **os.environ}
    server = values.get("POSTGRES_SERVER")
    user = values.get("POSTGRES_USER")
    password = values.get("POSTGRES_PASSWORD")
    port = values.get("POSTGRES_PORT") or "5432"
    if not (server and user and password):
        raise RuntimeError(
            "Tests need a local Postgres. Set POSTGRES_SERVER, POSTGRES_USER and "
            "POSTGRES_PASSWORD in the root .env (see .env.example) and run "
            "`make db`, or set TEST_DATABASE_URL to a database named 'app_test'."
        )

    from sqlalchemy.engine import URL

    return URL.create(
        "postgresql+psycopg",
        username=user,
        password=password,
        host=server,
        port=int(port),
        database=_TEST_DB_NAME,
    ).render_as_string(hide_password=False)


if _needs_app_db() and not os.environ.get("CI"):
    # Set before any `app.*` import: the environment variable overrides both
    # POSTGRES_* and any DATABASE_URL written in the root .env.
    os.environ["DATABASE_URL"] = _local_test_database_url()

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError

    from app.core.config import settings

    db_uri = str(settings.SQLALCHEMY_DATABASE_URI or "")
    if not db_uri.endswith(f"/{_TEST_DB_NAME}"):
        raise RuntimeError(
            "Test DB safety check failed: the test database must be named "
            f"'{_TEST_DB_NAME}', got {_redact(db_uri)}."
        )

    admin_uri = db_uri.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_uri, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": _TEST_DB_NAME},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{_TEST_DB_NAME}"'))
    except OperationalError as exc:
        reason = str(exc.orig).strip().splitlines()[-1] if exc.orig else "unreachable"
        raise RuntimeError(
            f"Cannot reach the test Postgres at {_redact(db_uri)}: {reason}. "
            "Start it with `make db`."
        ) from None
    finally:
        admin_engine.dispose()

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
