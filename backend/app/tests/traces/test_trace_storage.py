"""A trace is stored as rows and reads back exactly as it was sent."""

import pytest
from sqlmodel import Session, col, func, select

from app import crud
from app.models.call import Call, CallComponent, CallEvent
from app.models.enums import CallEventType, ToolCallStatus
from app.models.trace import Trace
from app.tests.traces.examples import EXAMPLE_NAMES, load_example
from app.tests.utils.eval import create_test_agent, get_test_company_id


def _store(db: Session, trace: Trace) -> Call:
    agent = create_test_agent(db)
    return crud.store_trace(
        session=db,
        trace=trace,
        agent_id=agent.id,
        company_id=get_test_company_id(db),
    )


def _count(
    db: Session, model: type[CallEvent] | type[CallComponent], call: Call
) -> int:
    return db.exec(
        select(func.count()).select_from(model).where(col(model.call_id) == call.id)
    ).one()


@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_example_survives_a_round_trip_through_the_database(
    db: Session, name: str
) -> None:
    trace = load_example(name)
    call = _store(db, trace)

    assert crud.get_trace(session=db, call=call) == trace


def test_each_event_and_component_is_one_row(db: Session) -> None:
    trace = load_example("hosted-platform-full")
    call = _store(db, trace)

    assert _count(db, CallEvent, call) == len(trace.events)
    assert _count(db, CallComponent, call) == len(trace.components or [])


def test_call_level_fields_are_columns(db: Session) -> None:
    call = _store(db, load_example("hosted-platform-full"))

    assert call.provider == "retell"
    assert call.external_id == "call_example_0001"
    assert call.provider_agent_id == "agent_example_71a"
    assert call.caller_number == "+15550123"
    assert call.end_reason == "transfer"
    assert call.schema_version == 1
    assert call.inputs == {"customer_name": "Dana", "plan": "standard"}


def test_tool_calls_can_be_aggregated_with_plain_sql(db: Session) -> None:
    call = _store(db, load_example("hosted-platform-partial"))

    rows = db.exec(
        select(CallEvent.name, CallEvent.status)
        .where(CallEvent.call_id == call.id)
        .where(CallEvent.type == CallEventType.TOOL_CALL)
        .order_by(col(CallEvent.seq))
    ).all()
    assert rows == [("lookup_order", None), ("lookup_order", ToolCallStatus.TIMEOUT)]


def test_event_order_is_preserved(db: Session) -> None:
    trace = load_example("hosted-platform-full")
    call = _store(db, trace)

    keys = db.exec(
        select(CallEvent.key)
        .where(CallEvent.call_id == call.id)
        .order_by(col(CallEvent.seq))
    ).all()
    assert list(keys) == [event.id for event in trace.events]


def test_storing_the_same_call_again_replaces_its_trace(db: Session) -> None:
    agent = create_test_agent(db)
    company_id = get_test_company_id(db)
    first = load_example("hosted-platform-full")
    shorter = first.model_copy(update={"events": first.events[:2], "components": None})

    call = crud.store_trace(
        session=db, trace=first, agent_id=agent.id, company_id=company_id
    )
    again = crud.store_trace(
        session=db, trace=shorter, agent_id=agent.id, company_id=company_id
    )

    assert again.id == call.id
    assert _count(db, CallEvent, again) == 2
    assert _count(db, CallComponent, again) == 0
    assert crud.get_trace(session=db, call=again) == shorter


def test_same_external_id_on_another_agent_is_a_different_call(db: Session) -> None:
    trace = load_example("self-hosted-text-only")
    first = _store(db, trace)
    second = _store(db, trace)

    assert first.id != second.id


def test_deleting_a_call_deletes_its_events_and_components(db: Session) -> None:
    call = _store(db, load_example("hosted-platform-full"))
    call_id = call.id

    db.delete(call)
    db.commit()

    assert (
        db.exec(
            select(func.count())
            .select_from(CallEvent)
            .where(CallEvent.call_id == call_id)
        ).one()
        == 0
    )
    assert (
        db.exec(
            select(func.count())
            .select_from(CallComponent)
            .where(CallComponent.call_id == call_id)
        ).one()
        == 0
    )


def test_a_call_without_a_trace_reads_as_none(db: Session) -> None:
    agent = create_test_agent(db)
    call = Call(
        company_id=get_test_company_id(db),
        agent_id=agent.id,
        provider="retell",
        external_id="synced-before-traces",
        provider_agent_id="agent_x",
        started_at=load_example("self-hosted-text-only").started_at.replace(
            tzinfo=None
        ),
    )
    db.add(call)
    db.commit()

    assert crud.get_trace(session=db, call=call) is None
