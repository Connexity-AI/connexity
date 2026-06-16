import uuid
from datetime import UTC, datetime

from sqlalchemy import func, text
from sqlmodel import Session, col, select

from app.models import (
    Agent,
    Difficulty,
    OnConflict,
    TestCase,
    TestCaseCreate,
    TestCaseImportItem,
    TestCaseImportResult,
    TestCaseStatus,
    TestCaseUpdate,
)


def create_test_case(
    *, session: Session, test_case_in: TestCaseCreate, company_id: uuid.UUID
) -> TestCase:
    if test_case_in.agent_id is not None:
        agent = session.get(Agent, test_case_in.agent_id)
        if agent is None or agent.company_id != company_id:
            msg = f"Agent not found: {test_case_in.agent_id}"
            raise ValueError(msg)
    db_obj = TestCase.model_validate(
        {**test_case_in.model_dump(), "company_id": company_id}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_test_case(
    *,
    session: Session,
    test_case_id: uuid.UUID,
    company_id: uuid.UUID | None = None,
    include_deleted: bool = False,
) -> TestCase | None:
    """Fetch a test case by id.

    Soft-deleted rows are hidden by default; pass ``include_deleted=True``
    to look up an already-deleted test case (e.g. when rendering a historical
    eval run that referenced it).
    """
    tc = session.get(TestCase, test_case_id)
    if tc is None:
        return None
    if tc.deleted_at is not None and not include_deleted:
        return None
    if company_id is not None and tc.company_id != company_id:
        return None
    return tc


def list_distinct_tags_for_agent(*, session: Session, agent_id: uuid.UUID) -> list[str]:
    """Return sorted distinct tags used on test cases bound to ``agent_id``."""
    statement = text(
        "SELECT DISTINCT t FROM test_case "
        "CROSS JOIN LATERAL unnest(tags) AS t "
        "WHERE agent_id = :aid AND deleted_at IS NULL AND cardinality(tags) > 0 "
        "ORDER BY t"
    )
    rows = session.execute(statement, {"aid": agent_id}).fetchall()
    return [str(r[0]) for r in rows if r[0]]


def list_recent_test_cases_for_agent(
    *, session: Session, agent_id: uuid.UUID, limit: int = 20
) -> list[TestCase]:
    """Most recently created test cases for an agent (for prompt context)."""
    statement = (
        select(TestCase)
        .where(
            TestCase.agent_id == agent_id,
            col(TestCase.deleted_at).is_(None),
        )
        .order_by(col(TestCase.created_at).desc())
        .limit(limit)
    )
    return list(session.exec(statement).all())


def list_test_cases(
    *,
    session: Session,
    company_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    tag: str | None = None,
    difficulty: Difficulty | None = None,
    status: TestCaseStatus | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    agent_id: uuid.UUID | None = None,
    include_deleted: bool = False,
) -> tuple[list[TestCase], int]:
    statement = select(TestCase).where(TestCase.company_id == company_id)
    count_statement = (
        select(func.count())
        .select_from(TestCase)
        .where(TestCase.company_id == company_id)
    )

    if not include_deleted:
        statement = statement.where(col(TestCase.deleted_at).is_(None))
        count_statement = count_statement.where(col(TestCase.deleted_at).is_(None))

    if tag is not None:
        statement = statement.where(col(TestCase.tags).any(tag))
        count_statement = count_statement.where(col(TestCase.tags).any(tag))
    if difficulty is not None:
        statement = statement.where(TestCase.difficulty == difficulty)
        count_statement = count_statement.where(TestCase.difficulty == difficulty)
    if status is not None:
        statement = statement.where(TestCase.status == status)
        count_statement = count_statement.where(TestCase.status == status)
    if agent_id is not None:
        statement = statement.where(TestCase.agent_id == agent_id)
        count_statement = count_statement.where(TestCase.agent_id == agent_id)
    if search is not None:
        pattern = f"%{search}%"
        search_filter = col(TestCase.name).ilike(pattern) | col(
            TestCase.description
        ).ilike(pattern)
        statement = statement.where(search_filter)
        count_statement = count_statement.where(search_filter)

    allowed_sort_fields = {"created_at", "updated_at", "name", "difficulty", "status"}
    if sort_by not in allowed_sort_fields:
        sort_by = "created_at"
    sort_column = getattr(TestCase, sort_by)
    order = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    statement = statement.order_by(order)

    count = session.exec(count_statement).one()
    items = list(session.exec(statement.offset(skip).limit(limit)).all())
    return items, count


def update_test_case(
    *, session: Session, db_test_case: TestCase, test_case_in: TestCaseUpdate
) -> TestCase:
    update_data = test_case_in.model_dump(exclude_unset=True)
    if "agent_id" in update_data and update_data["agent_id"] is not None:
        agent = session.get(Agent, update_data["agent_id"])
        if agent is None:
            msg = f"Agent not found: {update_data['agent_id']}"
            raise ValueError(msg)
    db_test_case.sqlmodel_update(update_data)
    session.add(db_test_case)
    session.commit()
    session.refresh(db_test_case)
    return db_test_case


def delete_test_case(*, session: Session, db_test_case: TestCase) -> None:
    """Soft-delete: stamp ``deleted_at`` so historical eval runs that
    reference this test case keep working while it's hidden from lists.
    """
    db_test_case.deleted_at = datetime.now(UTC)
    session.add(db_test_case)
    session.commit()


EXPORT_MAX_ROWS = 5000


def export_test_cases(
    *,
    session: Session,
    company_id: uuid.UUID,
    tag: str | None = None,
    difficulty: Difficulty | None = None,
    status: TestCaseStatus | None = None,
    agent_id: uuid.UUID | None = None,
) -> list[TestCase]:
    """Export test cases matching optional filters (capped at EXPORT_MAX_ROWS)."""
    statement = (
        select(TestCase)
        .where(col(TestCase.deleted_at).is_(None))
        .where(TestCase.company_id == company_id)
    )

    if tag is not None:
        statement = statement.where(col(TestCase.tags).any(tag))
    if difficulty is not None:
        statement = statement.where(TestCase.difficulty == difficulty)
    if status is not None:
        statement = statement.where(TestCase.status == status)
    if agent_id is not None:
        statement = statement.where(TestCase.agent_id == agent_id)

    statement = statement.limit(EXPORT_MAX_ROWS)
    return list(session.exec(statement).all())


def bulk_import_test_cases(
    *,
    session: Session,
    test_cases_in: list[TestCaseImportItem],
    company_id: uuid.UUID,
    on_conflict: OnConflict,
) -> TestCaseImportResult:
    """Import test cases in bulk. Handles ID conflicts via on_conflict strategy."""
    created = 0
    skipped = 0
    overwritten = 0
    errors: list[str] = []

    incoming_ids = [item.id for item in test_cases_in if item.id is not None]
    existing: dict[uuid.UUID, TestCase] = {}
    if incoming_ids:
        rows = session.exec(
            select(TestCase).where(
                col(TestCase.id).in_(incoming_ids),
                TestCase.company_id == company_id,
            )
        ).all()
        existing = {row.id: row for row in rows}

    for idx, item in enumerate(test_cases_in):
        try:
            if item.agent_id is not None:
                agent = session.get(Agent, item.agent_id)
                if agent is None or agent.company_id != company_id:
                    label = item.name if item.name else f"index {idx}"
                    errors.append(f"Item '{label}': Agent not found: {item.agent_id}")
                    continue

            data = item.model_dump(exclude_unset=True, exclude={"id"})

            if item.id is None:
                db_obj = TestCase.model_validate({**data, "company_id": company_id})
                session.add(db_obj)
                created += 1
            elif item.id in existing:
                if on_conflict == OnConflict.SKIP:
                    skipped += 1
                else:
                    existing[item.id].sqlmodel_update(data)
                    existing[item.id].deleted_at = None
                    session.add(existing[item.id])
                    overwritten += 1
            else:
                db_obj = TestCase.model_validate(
                    {**data, "id": item.id, "company_id": company_id}
                )
                session.add(db_obj)
                created += 1
        except Exception as exc:
            label = item.name if item.name else f"index {idx}"
            errors.append(f"Item '{label}': {exc}")

    if errors and created == 0 and overwritten == 0:
        session.rollback()
    else:
        session.commit()

    return TestCaseImportResult(
        created=created,
        skipped=skipped,
        overwritten=overwritten,
        total=len(test_cases_in),
        errors=errors,
    )
