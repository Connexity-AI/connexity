"""The spec as `get_spec`, `write_spec` and the web route answer it (plan
`plans/2026-11-14-spec-api.md`)."""

import uuid
from collections.abc import Sequence
from typing import NamedTuple

from sqlmodel import Session, col, select

from app import crud
from app.crud.spec import RuleInput, normalise, prompt_text, write_spec
from app.models.agent import Agent
from app.models.enums import SpecOrigin, SpecRuleTouches
from app.models.spec import (
    Spec,
    SpecChangesPublic,
    SpecGroupPublic,
    SpecPromptPublic,
    SpecPublic,
    SpecRulePublic,
    SpecState,
    SpecVersionPublic,
    SpecWrittenPublic,
)
from app.models.user import User

MAX_RULES = 500
MAX_RULE_LENGTH = 500
# A quote shorter than this is found in almost any prompt, so it proves nothing.
MIN_QUOTE_WORDS = 3


def spec_state(spec: Spec | None, current: str | None) -> SpecState:
    if spec is None:
        return "none"
    if spec.origin is SpecOrigin.ADOPTED:
        return "needs_review"
    if current is not None and current != spec.agent_version:
        return "needs_review"
    return "current"


def _author(session: Session, spec: Spec) -> str | None:
    if spec.created_by is not None:
        user = session.get(User, spec.created_by)
        if user is not None:
            return (user.full_name or "").strip() or user.email.split("@")[0]
    return spec.created_by_email.split("@")[0] if spec.created_by_email else None


def spec_answer(
    *,
    session: Session,
    agent: Agent,
    version: int | None = None,
    include_prompt: bool = False,
) -> SpecPublic | None:
    """The agent's spec, latest or ``version``. None when ``version`` does not exist."""
    latest = crud.latest_spec(session=session, agent_id=agent.id)
    spec = (
        crud.get_spec_version(session=session, agent_id=agent.id, version=version)
        if version is not None
        else latest
    )
    if version is not None and spec is None:
        return None
    current = crud.current_agent_version(session=session, agent_id=agent.id)
    categories = crud.list_categories(session=session)
    groups: list[SpecGroupPublic] = []
    summary = None
    if spec is not None:
        rules = crud.spec_rules(session=session, spec_id=spec.id)
        for category in categories:
            in_group = [r for r in rules if r.category_id == category.id]
            if in_group:
                groups.append(
                    SpecGroupPublic(
                        category=category.key,
                        name=category.name,
                        rules=[
                            SpecRulePublic(
                                key=r.key,
                                text=r.text,
                                source=r.source,
                                quote=r.quote,
                                touches=r.touches,
                            )
                            for r in in_group
                        ],
                    )
                )
        summary = SpecVersionPublic(
            version=spec.version,
            agent_version=spec.agent_version,
            origin=spec.origin,
            written_by=_author(session, spec),
            assistant=spec.assistant_name,
            created_at=spec.created_at,
            rule_count=len(rules),
        )
    prompt = None
    if include_prompt and current is not None:
        found = crud.agent_prompt(session=session, agent=agent, agent_version=current)
        if found is not None:
            prompt = SpecPromptPublic(
                kind=found.kind, version=found.version, content=found.content
            )
    return SpecPublic(
        agent_id=agent.id,
        agent_name=agent.name,
        current_agent_version=current,
        state=spec_state(latest, current),
        spec=summary,
        latest_version=latest.version if latest else None,
        groups=groups,
        prompt=prompt,
    )


class RuleDraft(NamedTuple):
    text: str
    category: str
    quote: str | None
    touches: SpecRuleTouches | None
    key: str | None


class SpecRefused(Exception):
    def __init__(self, error: str, problems: list[str]) -> None:
        super().__init__(error)
        self.error = error
        self.problems = problems


def write_agent_spec(
    *,
    session: Session,
    agent: Agent,
    drafts: Sequence[RuleDraft],
    author: User,
    assistant_name: str | None,
) -> SpecWrittenPublic:
    """Check ``drafts`` and store them as the agent's new spec version.

    Raises:
        SpecRefused: The agent has no version yet, or a rule is not right; every
            problem is listed.
    """
    current = crud.current_agent_version(session=session, agent_id=agent.id)
    if current is None:
        raise SpecRefused(
            "The agent has no calls yet, so its version is not known",
            ["Write its spec after its first call is stored."],
        )
    if not drafts:
        raise SpecRefused("A spec needs at least one rule", [])
    if len(drafts) > MAX_RULES:
        raise SpecRefused(f"A spec has at most {MAX_RULES} rules", [])

    categories = {c.key: c.id for c in crud.list_categories(session=session)}
    previous = crud.latest_spec(session=session, agent_id=agent.id)
    previous_keys = (
        {r.key for r in crud.spec_rules(session=session, spec_id=previous.id)}
        if previous
        else set()
    )
    prompt = crud.agent_prompt(session=session, agent=agent, agent_version=current)
    text = prompt_text(prompt.content) if prompt is not None else None

    problems: list[str] = []
    seen: set[str] = set()
    for n, draft in enumerate(drafts, start=1):
        rule = f"Rule {n}"
        if not draft.text.strip():
            problems.append(f"{rule}: the text is empty.")
        elif len(draft.text) > MAX_RULE_LENGTH:
            problems.append(f"{rule}: longer than {MAX_RULE_LENGTH} characters.")
        if draft.category not in categories:
            problems.append(
                f"{rule}: unknown category '{draft.category}'; use a key from "
                "`list_categories`."
            )
        if draft.key is not None:
            if draft.key in seen:
                problems.append(f"{rule}: key '{draft.key}' is used twice.")
            elif draft.key not in previous_keys:
                problems.append(
                    f"{rule}: key '{draft.key}' is not in the previous version; leave "
                    "the key out for a new rule."
                )
            seen.add(draft.key)
        quote = (draft.quote or "").strip()
        if not quote:
            problems.append(
                f"{rule}: quote the prompt's words it rests on; a rule the prompt "
                "does not state is a question for the person."
            )
        elif len(normalise(quote).split()) < MIN_QUOTE_WORDS:
            problems.append(
                f"{rule}: quote at least {MIN_QUOTE_WORDS} words of the prompt, so the "
                "rule can be traced to them."
            )
        elif text is not None and normalise(quote) not in text:
            problems.append(
                f"{rule}: the quote is not in the prompt of version {current}; quote "
                "its words exactly."
            )
    if problems:
        raise SpecRefused("The spec was not stored", problems)

    spec, before = write_spec(
        session=session,
        agent=agent,
        agent_version=current,
        prompt_fingerprint=prompt.fingerprint if prompt else None,
        rules=[
            RuleInput(
                text=d.text.strip(),
                category_id=categories[d.category],
                quote=(d.quote or "").strip(),
                touches=d.touches,
                key=d.key,
            )
            for d in drafts
        ],
        author=author,
        assistant_name=assistant_name,
    )
    kept = sum(1 for d in drafts if d.key is not None)
    answer = spec_answer(session=session, agent=agent)
    assert answer is not None
    return SpecWrittenPublic(
        **answer.model_dump(),
        changes=SpecChangesPublic(
            rules=len(drafts),
            kept=kept,
            added=len(drafts) - kept,
            dropped=len(previous_keys) - kept if before else 0,
            quotes_checked=text is not None,
        ),
    )


def agents_needing_specs(
    *, session: Session, company_id: uuid.UUID
) -> list[tuple[Agent, SpecState]]:
    """Linked agents with calls whose spec is missing or needs review, by name."""
    agents = list(
        session.exec(
            select(Agent)
            .where(
                Agent.company_id == company_id,
                col(Agent.integration_id).is_not(None),
                col(Agent.platform_agent_id).is_not(None),
            )
            .order_by(col(Agent.name))
        ).all()
    )
    ids = [a.id for a in agents]
    specs = crud.latest_specs(session=session, agent_ids=ids)
    currents = crud.current_agent_versions(session=session, agent_ids=ids)
    out = []
    for agent in agents:
        if agent.id not in currents:
            continue  # no calls yet: its version, and so its spec, waits
        state = spec_state(specs.get(agent.id), currents.get(agent.id))
        if state != "current":
            out.append((agent, state))
    return out
