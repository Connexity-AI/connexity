"""Schema-level guarantees: models and migrations agree, and enums are stored by value."""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

from app import crud
from app.core.db import engine
from app.models import AgentCreateDraft, AgentVersion
from app.models.enums import AgentMode, AgentVersionStatus, Platform
from app.tests.utils.eval import create_test_agent, get_test_company_id


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
    assert row[0] == AgentMode.ENDPOINT.value

    status = db.execute(
        text("SELECT status FROM agent_version WHERE agent_id = :id"),
        {"id": agent.id},
    ).one()
    assert status[0] == AgentVersionStatus.PUBLISHED.value


def test_only_one_draft_per_agent_is_allowed(db: Session) -> None:
    company_id = get_test_company_id(db)
    agent = crud.create_draft_agent(
        session=db,
        body=AgentCreateDraft(name="draft-only", platform=Platform.WEBHOOK),
        company_id=company_id,
    )
    db.add(
        AgentVersion(
            agent_id=agent.id,
            company_id=company_id,
            version=None,
            status=AgentVersionStatus.DRAFT,
            mode=AgentMode.PLATFORM,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
