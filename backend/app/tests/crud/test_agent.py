from sqlmodel import Session

from app import crud
from app.tests.utils.eval import create_test_agent


def test_get_agent(db: Session) -> None:
    agent = create_test_agent(db)
    fetched = crud.get_agent(session=db, agent_id=agent.id)
    assert fetched is not None
    assert fetched.id == agent.id
    assert fetched.name == agent.name


def test_get_agent_not_found(db: Session) -> None:
    import uuid

    fetched = crud.get_agent(session=db, agent_id=uuid.uuid4())
    assert fetched is None
