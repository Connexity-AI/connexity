"""Reading, writing and adopting specs (plans `plans/2026-11-14-spec.md` and
`plans/2026-11-14-spec-api.md`).

An agent's current version is the agent version of its most recent call. Spec versions
are numbered per agent; the highest is the agent's spec. Rules are never edited: every
write is a new version.
"""

import json
import logging
import re
import uuid
from typing import Any, NamedTuple

from sqlmodel import Session, col, func, select

from app.crud.check import lock_agent
from app.models.agent import Agent
from app.models.call import Call
from app.models.component_version import ComponentVersion
from app.models.enums import SpecOrigin, SpecRuleSource, SpecRuleTouches
from app.models.spec import Spec, SpecRule
from app.models.user import User

logger = logging.getLogger(__name__)

# The kinds that hold an agent version's instructions in the catalogue.
PROMPT_KINDS = ("prompt", "flow")
_NOT_WORDS = re.compile(r"[\W_]+", re.UNICODE)


def current_agent_version(*, session: Session, agent_id: uuid.UUID) -> str | None:
    """The agent version of the agent's most recent call that records one."""
    return session.exec(
        select(Call.agent_version)
        .where(
            Call.agent_id == agent_id,
            col(Call.deleted_at).is_(None),
            col(Call.agent_version).is_not(None),
        )
        .order_by(col(Call.started_at).desc(), col(Call.id).desc())
        .limit(1)
    ).first()


def latest_spec(*, session: Session, agent_id: uuid.UUID) -> Spec | None:
    return session.exec(
        select(Spec)
        .where(Spec.agent_id == agent_id)
        .order_by(col(Spec.version).desc())
        .limit(1)
    ).first()


def latest_specs(
    *, session: Session, agent_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Spec]:
    """Each agent's latest spec version, for those that have one."""
    if not agent_ids:
        return {}
    newest = (
        select(Spec.agent_id, func.max(col(Spec.version)).label("version"))
        .where(col(Spec.agent_id).in_(agent_ids))
        .group_by(col(Spec.agent_id))
        .subquery()
    )
    rows = session.exec(
        select(Spec).join(
            newest,
            (col(Spec.agent_id) == newest.c.agent_id)
            & (col(Spec.version) == newest.c.version),
        )
    ).all()
    return {spec.agent_id: spec for spec in rows}


def current_agent_versions(
    *, session: Session, agent_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """Each agent's current version, for those whose calls record one."""
    if not agent_ids:
        return {}
    ranked = (
        select(
            Call.agent_id,
            Call.agent_version,
            func.row_number()
            .over(
                partition_by=col(Call.agent_id),
                order_by=(col(Call.started_at).desc(), col(Call.id).desc()),
            )
            .label("rank"),
        )
        .where(
            col(Call.agent_id).in_(agent_ids),
            col(Call.deleted_at).is_(None),
            col(Call.agent_version).is_not(None),
        )
        .subquery()
    )
    rows = session.exec(
        select(ranked.c.agent_id, ranked.c.agent_version).where(ranked.c.rank == 1)
    ).all()
    return {agent_id: version for agent_id, version in rows if version}


def get_spec_version(
    *, session: Session, agent_id: uuid.UUID, version: int
) -> Spec | None:
    return session.exec(
        select(Spec).where(Spec.agent_id == agent_id, Spec.version == version)
    ).first()


def spec_rules(*, session: Session, spec_id: uuid.UUID) -> list[SpecRule]:
    return list(
        session.exec(
            select(SpecRule)
            .where(SpecRule.spec_id == spec_id)
            .order_by(col(SpecRule.position), col(SpecRule.key))
        ).all()
    )


class AgentPrompt(NamedTuple):
    kind: str  # prompt or flow
    version: str
    fingerprint: str
    content: Any


def agent_prompt(
    *, session: Session, agent: Agent, agent_version: str
) -> AgentPrompt | None:
    """The prompt or flow that served ``agent_version``, from the catalogue."""
    if not agent.platform_agent_id:
        return None
    row = session.exec(
        select(ComponentVersion).where(
            ComponentVersion.agent_id == agent.id,
            ComponentVersion.kind == "agent",
            ComponentVersion.ref == agent.platform_agent_id,
            ComponentVersion.version == agent_version,
        )
    ).first()
    if row is None:
        return None
    for link in row.links or []:
        if link.get("kind") not in PROMPT_KINDS:
            continue
        prompt = session.exec(
            select(ComponentVersion).where(
                ComponentVersion.agent_id == agent.id,
                ComponentVersion.kind == link["kind"],
                ComponentVersion.ref == link["ref"],
                ComponentVersion.version == link["version"],
            )
        ).first()
        if prompt is not None:
            return AgentPrompt(
                kind=prompt.kind,
                version=prompt.version,
                fingerprint=prompt.fingerprint,
                content=prompt.content,
            )
    return None


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _strings(item)]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return []


def normalise(text: str) -> str:
    """Lower case, with punctuation and runs of spaces as one space."""
    return " ".join(_NOT_WORDS.sub(" ", text.lower()).split())


def prompt_text(content: Any) -> str:
    """Every piece of text in a prompt or flow, normalised, for checking quotes."""
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except ValueError:
            pass
    return normalise(" ".join(_strings(content)))


class RuleInput(NamedTuple):
    text: str
    category_id: uuid.UUID
    quote: str | None
    touches: SpecRuleTouches | None
    key: str | None


def write_spec(
    *,
    session: Session,
    agent: Agent,
    agent_version: str,
    prompt_fingerprint: str | None,
    rules: list[RuleInput],
    author: User,
    assistant_name: str | None,
) -> tuple[Spec, Spec | None]:
    """A new spec version with ``rules`` for ``agent_version``. Commits.

    Rules keep their key when given one; new rules get a fresh key. Positions follow
    the order the rules were given, within each category.

    Two writes for one agent are made in turn: the agent row is locked, so each takes
    the next version number.

    Returns:
        The new version, and the version it follows.
    """
    lock_agent(session=session, agent_id=agent.id)
    previous = latest_spec(session=session, agent_id=agent.id)
    spec = Spec(
        company_id=agent.company_id,
        agent_id=agent.id,
        version=(previous.version + 1) if previous else 1,
        agent_version=agent_version,
        prompt_fingerprint=prompt_fingerprint,
        origin=SpecOrigin.WRITTEN,
        previous_id=previous.id if previous else None,
        created_by=author.id,
        created_by_email=author.email,
        assistant_name=assistant_name,
    )
    session.add(spec)
    session.flush()
    positions: dict[uuid.UUID, int] = {}
    for rule in rules:
        positions[rule.category_id] = positions.get(rule.category_id, 0) + 1
        session.add(
            SpecRule(
                company_id=agent.company_id,
                spec_id=spec.id,
                key=rule.key or uuid.uuid4().hex[:12],
                position=positions[rule.category_id],
                category_id=rule.category_id,
                text=rule.text,
                source=SpecRuleSource.PROMPT,
                quote=rule.quote,
                touches=rule.touches,
            )
        )
    session.commit()
    session.refresh(spec)
    return spec, previous


def _adopt(session: Session, agent_id: uuid.UUID) -> Spec | None:
    previous = latest_spec(session=session, agent_id=agent_id)
    if previous is None:
        return None
    current = current_agent_version(session=session, agent_id=agent_id)
    if current is None or current == previous.agent_version:
        return None
    # Made in turn with spec writes; read the latest again under the lock.
    lock_agent(session=session, agent_id=agent_id)
    previous = latest_spec(session=session, agent_id=agent_id)
    if previous is None or current == previous.agent_version:
        session.rollback()
        return None
    agent = session.get(Agent, agent_id)
    if agent is None:
        return None
    prompt = agent_prompt(session=session, agent=agent, agent_version=current)
    spec = Spec(
        company_id=previous.company_id,
        agent_id=agent_id,
        version=previous.version + 1,
        agent_version=current,
        prompt_fingerprint=prompt.fingerprint if prompt else None,
        origin=SpecOrigin.ADOPTED,
        previous_id=previous.id,
    )
    session.add(spec)
    session.flush()
    for rule in spec_rules(session=session, spec_id=previous.id):
        session.add(
            SpecRule(
                company_id=rule.company_id,
                spec_id=spec.id,
                key=rule.key,
                position=rule.position,
                category_id=rule.category_id,
                text=rule.text,
                source=rule.source,
                quote=rule.quote,
                clarification_id=rule.clarification_id,
                touches=rule.touches,
            )
        )
    session.commit()
    return spec


def adopt_spec_safely(*, session: Session, agent_id: uuid.UUID) -> Spec | None:
    """When the agent's current version has moved past its spec's, copy the spec to it.

    Called after a call is stored. Only the agent's most recent call moves its current
    version, so a late older call adopts nothing. A failure is logged and never stops
    the call being stored. Two stores at once may race; the unique version per agent
    lets only one adoption in.
    """
    try:
        return _adopt(session, agent_id)
    except Exception:
        session.rollback()
        logger.exception("Adopting the spec failed for agent %s", agent_id)
        return None
