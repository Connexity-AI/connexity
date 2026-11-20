"""Migration 0039: runs of scenarios stored without a version are deleted with their
simulated calls and verdicts; runs with no scope stay (plan
`plans/2026-11-19-tests-tab-versions-fix.md`)."""

import importlib
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlmodel import Session

from app.core.db import engine
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    _agent,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)

migration = importlib.import_module("app.alembic.versions.0039_runs_have_a_version")


def _run(
    conn: object,
    run_id: uuid.UUID,
    agent_id: object,
    company_id: object,
    scope: str | None,
    version: str | None,
) -> None:
    conn.execute(  # type: ignore[attr-defined]
        text(
            "INSERT INTO run (id, agent_id, company_id, scope, platform_version, "
            "status, agent_mode, created_at, updated_at) VALUES "
            "(:id, :agent, :company, :scope, :version, 'completed', "
            "'platform', now(), now())"
        ),
        {
            "id": run_id,
            "agent": agent_id,
            "company": company_id,
            "scope": scope,
            "version": version,
        },
    )


def test_runs_without_a_version_go_and_the_rest_stay(db: Session) -> None:
    user = _person(db)
    agent = _agent(db, user, "Invented")
    no_version, pinned, legacy = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    with engine.connect() as conn:
        tx = conn.begin()
        try:
            # As before the migration: no check yet.
            conn.execute(
                text("ALTER TABLE run DROP CONSTRAINT ck_run_scenarios_have_a_version")
            )
            _run(conn, no_version, agent.id, agent.company_id, "all", None)
            _run(conn, pinned, agent.id, agent.company_id, "all", "15")
            _run(conn, legacy, agent.id, agent.company_id, None, None)

            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()

            left = set(
                conn.execute(
                    text("SELECT id FROM run WHERE agent_id = :agent"),
                    {"agent": agent.id},
                ).scalars()
            )
            assert left == {pinned, legacy}
            # The check is back.
            checks = conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conname = 'ck_run_scenarios_have_a_version'"
                )
            ).all()
            assert len(checks) == 1
        finally:
            tx.rollback()
