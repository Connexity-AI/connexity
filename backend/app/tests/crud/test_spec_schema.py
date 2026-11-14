"""The spec tables' rules, enforced by the database (plan `plans/2026-11-14-spec.md`)."""

import uuid
from collections.abc import Callable

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app import crud
from app.models import Agent, Category, Spec, SpecRule, UserCreate
from app.models.enums import (
    CategoryKind,
    SpecOrigin,
    SpecRuleSource,
    SpecRuleTouches,
)
from app.tests.utils.utils import random_email, random_lower_string


def _agent(db: Session) -> Agent:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    agent = Agent(name="Front desk", company_id=user.company_id)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _category(db: Session, key: str = "booking") -> Category:
    return db.exec(select(Category).where(Category.key == key)).one()


def _spec(db: Session, agent: Agent, version: int = 1, **fields: object) -> Spec:
    spec = Spec(
        company_id=agent.company_id,
        agent_id=agent.id,
        version=version,
        agent_version="14",
        **({"origin": SpecOrigin.WRITTEN} | fields),
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec


def _rule(
    db: Session,
    spec: Spec,
    key: str,
    *,
    position: int = 1,
    category_id: uuid.UUID | None = None,
    touches: SpecRuleTouches | None = None,
) -> SpecRule:
    rule = SpecRule(
        company_id=spec.company_id,
        spec_id=spec.id,
        key=key,
        position=position,
        category_id=category_id or _category(db).id,
        text="Never book a slot outside opening hours",
        source=SpecRuleSource.PROMPT,
        quote="Only book within opening hours",
        touches=touches,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def _refused(db: Session, write: Callable[[], object]) -> None:
    with pytest.raises(IntegrityError):
        write()
    db.rollback()


def test_a_spec_and_its_rules_are_stored_as_written(db: Session) -> None:
    agent = _agent(db)
    first = _spec(db, agent)
    second = _spec(
        db, agent, version=2, origin=SpecOrigin.ADOPTED, previous_id=first.id
    )
    rule = _rule(db, second, "r1", touches=SpecRuleTouches.MONEY)

    assert (second.version, second.origin, second.previous_id) == (
        2,
        SpecOrigin.ADOPTED,
        first.id,
    )
    assert second.created_at is not None
    assert (rule.source, rule.quote, rule.touches) == (
        SpecRuleSource.PROMPT,
        "Only book within opening hours",
        SpecRuleTouches.MONEY,
    )
    assert rule.clarification_id is None


def test_spec_versions_are_unique_per_agent(db: Session) -> None:
    agent = _agent(db)
    other = _agent(db)
    _spec(db, agent)
    # Another agent can have its own version 1.
    _spec(db, other)

    _refused(db, lambda: _spec(db, agent))


def test_rule_keys_are_unique_within_a_version(db: Session) -> None:
    agent = _agent(db)
    first = _spec(db, agent)
    second = _spec(db, agent, version=2)
    _rule(db, first, "r1")
    # The same rule kept in the next version carries the same key.
    _rule(db, second, "r1")

    _refused(db, lambda: _rule(db, first, "r1", position=2))


def test_deleting_an_agent_removes_its_specs_and_rules(db: Session) -> None:
    agent = _agent(db)
    spec = _spec(db, agent)
    rule = _rule(db, spec, "r1")
    spec_id, rule_id = spec.id, rule.id

    db.delete(agent)
    db.commit()
    db.expunge_all()

    assert db.get(Spec, spec_id) is None
    assert db.get(SpecRule, rule_id) is None


def test_a_category_in_use_cannot_be_deleted(db: Session) -> None:
    agent = _agent(db)
    spare = Category(
        key=f"spare_{uuid.uuid4().hex[:6]}",
        name="Spare",
        position=99,
        kind=CategoryKind.BEHAVIOUR,
    )
    db.add(spare)
    db.commit()
    _rule(db, _spec(db, agent), "r1", category_id=spare.id)

    def delete() -> None:
        db.delete(spare)
        db.commit()

    _refused(db, delete)


def test_deleting_a_spec_version_keeps_the_next_and_drops_its_link(db: Session) -> None:
    agent = _agent(db)
    first = _spec(db, agent)
    second = _spec(db, agent, version=2, previous_id=first.id)

    db.delete(first)
    db.commit()
    db.refresh(second)

    assert second.previous_id is None


def test_every_spec_row_carries_its_workspace() -> None:
    for table in (Spec, SpecRule):
        column = table.__table__.columns["company_id"]  # type: ignore[attr-defined]
        assert column.nullable is False
        assert {fk.column.table.name for fk in column.foreign_keys} == {"company"}
