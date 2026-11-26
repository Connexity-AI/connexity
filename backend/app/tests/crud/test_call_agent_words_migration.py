"""Migration 0055: calls stored before it get the agent's word count from their events,
counted as `app/services/grading.py` counts (plan
`plans/2026-11-26-call-must-qualify.md`). Calls are invented."""

import importlib

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlmodel import Session

from app.core.db import engine
from app.tests.api.routes.test_calls_list import (  # noqa: F401
    _agent,
    _call,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)

migration = importlib.import_module("app.alembic.versions.0055_call_agent_words")


def test_stored_calls_get_the_same_count_as_new_ones(db: Session) -> None:
    user = _person(db)
    desk = _agent(db, user.company_id, user.id, "Front desk")
    calls = [
        _call(db, desk, caller="+17325550011", minutes_ago=1, agent_line="Hi there"),
        _call(
            db,
            desk,
            caller="+17325550012",
            minutes_ago=2,
            agent_line="  Hello,   thanks for calling.\nHow can I help you today? ",
            caller_line="I would like to book a cleaning next week please",
        ),
    ]
    expected = {call.id: call.agent_words for call in calls}
    assert expected[calls[0].id] == 2
    assert expected[calls[1].id] == 10
    # End the session's transaction, or its read lock on `call` blocks the ALTER below.
    db.commit()

    with engine.connect() as conn:
        tx = conn.begin()
        try:
            # As before the migration: no column yet.
            conn.execute(text("ALTER TABLE call DROP COLUMN agent_words"))
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
            counted = dict(
                conn.execute(  # type: ignore[arg-type]
                    text("SELECT id, agent_words FROM call WHERE agent_id = :agent"),
                    {"agent": desk.id},
                ).all()
            )
            assert counted == expected
        finally:
            tx.rollback()
