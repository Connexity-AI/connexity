import uuid

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import TestCaseResult, TestCaseResultCreate, TestCaseResultUpdate


def create_test_case_result(
    *, session: Session, result_in: TestCaseResultCreate
) -> TestCaseResult:
    db_obj = TestCaseResult.model_validate(result_in)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_test_case_result(
    *, session: Session, result_id: uuid.UUID
) -> TestCaseResult | None:
    return session.get(TestCaseResult, result_id)


def list_test_case_results(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    run_id: uuid.UUID | None = None,
    test_case_id: uuid.UUID | None = None,
    repetition_index: int | None = None,
    passed: bool | None = None,
) -> tuple[list[TestCaseResult], int]:
    statement = select(TestCaseResult)
    count_statement = select(func.count()).select_from(TestCaseResult)

    if run_id is not None:
        statement = statement.where(TestCaseResult.run_id == run_id)
        count_statement = count_statement.where(TestCaseResult.run_id == run_id)
    if test_case_id is not None:
        statement = statement.where(TestCaseResult.test_case_id == test_case_id)
        count_statement = count_statement.where(
            TestCaseResult.test_case_id == test_case_id
        )
    if repetition_index is not None:
        statement = statement.where(TestCaseResult.repetition_index == repetition_index)
        count_statement = count_statement.where(
            TestCaseResult.repetition_index == repetition_index
        )
    if passed is not None:
        statement = statement.where(TestCaseResult.passed == passed)
        count_statement = count_statement.where(TestCaseResult.passed == passed)

    count = session.exec(count_statement).one()
    items = list(session.exec(statement.offset(skip).limit(limit)).all())
    return items, count


def update_test_case_result(
    *,
    session: Session,
    db_result: TestCaseResult,
    result_in: TestCaseResultUpdate,
) -> TestCaseResult:
    update_data = result_in.model_dump(exclude_unset=True)
    if "transcript" in update_data and result_in.transcript is not None:
        update_data["transcript"] = [
            t.model_dump(mode="json") for t in result_in.transcript
        ]
    if "verdict" in update_data and result_in.verdict is not None:
        update_data["verdict"] = result_in.verdict.model_dump(mode="json")
    db_result.sqlmodel_update(update_data)
    session.add(db_result)
    session.commit()
    session.refresh(db_result)
    return db_result


def delete_test_case_result(*, session: Session, db_result: TestCaseResult) -> None:
    session.delete(db_result)
    session.commit()
