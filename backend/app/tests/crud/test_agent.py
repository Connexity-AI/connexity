from sqlmodel import Session

from app import crud
from app.models import AgentCreate, AgentUpdate
from app.tests.utils.eval import create_test_agent


def test_create_agent(db: Session) -> None:
    agent_in = AgentCreate(
        name="CRUD Test Agent",
        endpoint_url="http://example.com/agent",
        description="Created by test",
    )
    agent = crud.create_agent(session=db, agent_in=agent_in)
    assert agent.name == "CRUD Test Agent"
    assert agent.endpoint_url == "http://example.com/agent"
    assert agent.id is not None
    assert agent.created_at is not None


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


def test_list_agents(db: Session) -> None:
    create_test_agent(db)
    create_test_agent(db)
    items, count = crud.list_agents(session=db)
    assert count >= 2
    assert len(items) >= 2


def test_list_agents_pagination(db: Session) -> None:
    items, count = crud.list_agents(session=db, skip=0, limit=1)
    assert len(items) == 1
    assert count >= 1


def test_update_agent(db: Session) -> None:
    agent = create_test_agent(db)
    updated = crud.update_agent(
        session=db,
        db_agent=agent,
        agent_in=AgentUpdate(name="Updated Name"),
    )
    assert updated.name == "Updated Name"
    assert updated.id == agent.id


def test_delete_agent(db: Session) -> None:
    agent = create_test_agent(db)
    agent_id = agent.id
    crud.delete_agent(session=db, db_agent=agent)
    fetched = crud.get_agent(session=db, agent_id=agent_id)
    assert fetched is None
