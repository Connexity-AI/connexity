"""Schema-level guarantees: models and migrations agree, and enums are stored by value."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text
from sqlmodel import Session, SQLModel

from app.core.db import engine
from app.models.enums import AgentMode
from app.tests.utils.eval import create_test_agent


def test_models_match_migrated_schema() -> None:
    """A model change without a migration (or the reverse) fails here."""
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        diff = compare_metadata(context, SQLModel.metadata)
    assert diff == []


def test_every_enum_column_is_a_varchar_of_values() -> None:
    for table in SQLModel.metadata.tables.values():
        for column in table.columns:
            if not isinstance(column.type, SAEnum):
                continue
            where = f"{table.name}.{column.name}"
            assert column.type.native_enum is False, where
            enum_class = column.type.enum_class
            assert enum_class is not None, where
            assert column.type.enums == [member.value for member in enum_class], where


def test_enum_values_are_stored_lowercase(db: Session) -> None:
    agent = create_test_agent(db)
    row = db.execute(
        text("SELECT mode FROM agent WHERE id = :id"), {"id": agent.id}
    ).one()
    assert row[0] == AgentMode(agent.mode).value
    assert row[0] == row[0].lower()
