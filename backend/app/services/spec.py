"""The spec as `get_spec`, `write_spec` and the web route answer it (plan
`plans/2026-11-14-spec-api.md`)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Literal, NamedTuple

from sqlmodel import Session, col, select

from app import crud
from app.crud.check import lock_agent
from app.crud.clarification import state_counts, unanswered
from app.crud.scenario import scenarios_by_rule
from app.crud.spec import RuleInput, mark_critical, normalise, prompt_text, write_spec
from app.models.agent import Agent
from app.models.clarification import Clarification
from app.models.enums import ClarificationState, SpecRuleSource, SpecRuleTouches
from app.models.spec import (
    Spec,
    SpecChangesPublic,
    SpecComparisonPublic,
    SpecCountsPublic,
    SpecGroupPublic,
    SpecPublic,
    SpecRule,
    SpecRulePublic,
    SpecState,
    SpecVersionPublic,
    SpecWrittenPublic,
)
from app.models.user import User
from app.services.test_run import RuleMark, version_number, version_tested

MAX_RULES = 500
type RuleChange = Literal["kept", "added", "dropped"]
MAX_RULE_LENGTH = 500
# A quote shorter than this is found in almost any prompt, so it proves nothing.
MIN_QUOTE_WORDS = 3


def spec_state(spec: Spec | None, current: str | None) -> SpecState:
    """Current while its prompt rules were written for the agent's current version.

    An adopted version, or an answered one built on it, keeps the agent version its
    rules were last written for, so it needs review until the assistant writes the spec
    for the new prompt.
    """
    if spec is None:
        return "none"
    if spec.written_for is None or spec.written_for != (current or spec.agent_version):
        return "needs_review"
    return "current"


def _author(session: Session, spec: Spec) -> str | None:
    if spec.created_by is not None:
        user = session.get(User, spec.created_by)
        if user is not None:
            return (user.full_name or "").strip() or user.email.split("@")[0]
    return spec.created_by_email.split("@")[0] if spec.created_by_email else None


def _version_public(session: Session, spec: Spec, rule_count: int) -> SpecVersionPublic:
    return SpecVersionPublic(
        version=spec.version,
        agent_version=spec.agent_version,
        origin=spec.origin,
        written_by=_author(session, spec),
        assistant=spec.assistant_name,
        created_at=spec.created_at,
        rule_count=rule_count,
    )


def _answers(
    session: Session, rules: list[SpecRule]
) -> dict[uuid.UUID, tuple[str | None, datetime | None]]:
    """Who answered, and when, each clarification behind ``rules``."""
    ids = {r.clarification_id for r in rules if r.clarification_id}
    if not ids:
        return {}
    found = session.exec(
        select(Clarification).where(col(Clarification.id).in_(ids))
    ).all()
    user_ids = {c.decided_by for c in found if c.decided_by}
    users = {
        u.id: u
        for u in session.exec(select(User).where(col(User.id).in_(user_ids))).all()
    }
    out: dict[uuid.UUID, tuple[str | None, datetime | None]] = {}
    for c in found:
        user = users.get(c.decided_by) if c.decided_by else None
        if user is not None:
            name = (user.full_name or "").strip() or user.email.split("@")[0]
        else:
            name = c.decided_by_email.split("@")[0] if c.decided_by_email else None
        out[c.id] = (name, c.decided_at)
    return out


def spec_in_force(*, session: Session, agent: Agent, agent_version: str) -> int | None:
    """The spec version in force for an agent version: the newest one written for it
    or an earlier one (a spec stays in force until the next is written)."""
    wanted = version_number(agent_version)[0]
    best: tuple[int, int] | None = None
    for spec, _count in crud.spec_versions(session=session, agent_id=agent.id):
        written = version_number(spec.agent_version)[0]
        if spec.agent_version == agent_version:
            written = max(written, wanted)
        elif not (wanted >= 0 and 0 <= written <= wanted):
            continue
        # The spec written for the highest such agent version, newest spec first.
        key = (written, spec.version)
        if best is None or key > best:
            best = key
    return best[1] if best else None


def spec_answer(
    *,
    session: Session,
    agent: Agent,
    version: int | None = None,
    compare: int | None = None,
    for_version: str | None = None,
) -> SpecPublic | None:
    """The agent's spec, latest or ``version``, optionally compared with an earlier
    version ``compare``. None when ``version`` or ``compare`` does not exist.

    With ``for_version`` (an agent version) and no ``version``, the spec in force for
    it; none in force answers without a spec (``for_version`` says which was asked).
    Rule results then come from that agent version's latest full run.

    Compared, a rule is kept when the earlier version has its key with the same text;
    one whose text changed reads as the old text dropped and the new text added.
    """
    if for_version is not None and version is None:
        version = spec_in_force(session=session, agent=agent, agent_version=for_version)
        if version is None:
            answer = spec_answer(session=session, agent=agent)
            if answer is None:
                return None
            return answer.model_copy(
                update={
                    "spec": None,
                    "groups": [],
                    "counts": None,
                    "comparison": None,
                    "for_version": for_version,
                    "results_version": None,
                    "results_at": None,
                }
            )
    latest = crud.latest_spec(session=session, agent_id=agent.id)
    spec = (
        crud.get_spec_version(session=session, agent_id=agent.id, version=version)
        if version is not None
        else latest
    )
    if version is not None and spec is None:
        return None
    earlier = (
        crud.get_spec_version(session=session, agent_id=agent.id, version=compare)
        if compare is not None
        else None
    )
    if compare is not None and earlier is None:
        return None
    current = crud.current_agent_version(session=session, agent_id=agent.id)
    categories = crud.list_categories(session=session)
    groups: list[SpecGroupPublic] = []
    summary = None
    counts = None
    comparison = None
    results_version: str | None = None
    results_at: datetime | None = None
    if spec is not None:
        rules = crud.spec_rules(session=session, spec_id=spec.id)
        old_rules = (
            crud.spec_rules(session=session, spec_id=earlier.id) if earlier else []
        )
        old_text = {r.key: r.text for r in old_rules}
        new_text = {r.key: r.text for r in rules}
        dropped = [r for r in old_rules if new_text.get(r.key) != r.text]
        conflicts = (
            {
                c.replaces_key
                for c in unanswered(session=session, agent_id=agent.id)
                if c.replaces_key
            }
            if latest is not None and spec.id == latest.id
            else set()
        )
        answers = _answers(session, rules + dropped)
        listed = scenarios_by_rule(session=session, agent_id=agent.id)

        # Each rule's result in the live version's latest full run, on the latest
        # spec only: an older version's keys may mean other words.
        marks: dict[str, RuleMark] = {}
        if for_version is not None or (latest is not None and spec.id == latest.id):
            tested = version_tested(session, agent, for_version)
            results_version = tested.results.version
            results_at = tested.full_run.completed_at if tested.full_run else None
            marks = tested.marks

        def public(r: SpecRule, change: RuleChange | None) -> SpecRulePublic:
            who, when = (
                answers.get(r.clarification_id, (None, None))
                if (r.clarification_id)
                else (None, None)
            )
            return SpecRulePublic(
                key=r.key,
                text=r.text,
                source=r.source,
                quote=r.quote,
                touches=r.touches,
                critical=r.critical,
                scenarios=listed.get(r.key, 0) if change != "dropped" else 0,
                answered_by=who,
                answered_at=when,
                in_conflict=change != "dropped" and r.key in conflicts,
                change=change,
                result=None
                if change == "dropped" or marks.get(r.key) == "not_judged"
                else marks.get(r.key),  # type: ignore[arg-type]
            )

        def change_of(r: SpecRule) -> RuleChange | None:
            if earlier is None:
                return None
            return "kept" if old_text.get(r.key) == r.text else "added"

        for category in categories:
            shown = [
                public(r, change_of(r)) for r in rules if r.category_id == category.id
            ]
            shown += [
                public(r, "dropped") for r in dropped if r.category_id == category.id
            ]
            if shown:
                groups.append(
                    SpecGroupPublic(
                        category=category.key, name=category.name, rules=shown
                    )
                )
        summary = _version_public(session, spec, len(rules))
        from_clarifications = sum(
            1 for r in rules if r.source is SpecRuleSource.CLARIFICATION
        )
        counts = SpecCountsPublic(
            from_prompt=len(rules) - from_clarifications,
            from_clarifications=from_clarifications,
            in_conflict=sum(1 for r in rules if r.key in conflicts),
            critical=sum(1 for r in rules if r.critical),
        )
        if earlier is not None:
            kept = sum(1 for r in rules if old_text.get(r.key) == r.text)
            comparison = SpecComparisonPublic(
                version=earlier.version,
                kept=kept,
                added=len(rules) - kept,
                dropped=len(dropped),
            )
    versions = [
        _version_public(session, v, n)
        for v, n in crud.spec_versions(session=session, agent_id=agent.id)
    ]
    return SpecPublic(
        agent_id=agent.id,
        agent_name=agent.name,
        current_agent_version=current,
        state=spec_state(latest, current),
        spec=summary,
        latest_version=latest.version if latest else None,
        groups=groups,
        open_clarifications=state_counts(
            session=session, company_id=agent.company_id, agent_id=agent.id
        )[ClarificationState.OPEN],
        counts=counts,
        versions=versions,
        comparison=comparison,
        results_version=results_version,
        results_at=results_at,
        for_version=for_version,
    )


class RuleDraft(NamedTuple):
    text: str
    category: str
    quote: str | None
    touches: SpecRuleTouches | None
    key: str | None
    critical: bool | None = None


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
    previous_rules = (
        crud.spec_rules(session=session, spec_id=previous.id) if previous else []
    )
    # Rules from answered clarifications are carried over by Connexity, not rewritten.
    answered_keys = {
        r.key for r in previous_rules if r.source is SpecRuleSource.CLARIFICATION
    }
    previous_keys = {r.key for r in previous_rules} - answered_keys
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
            elif draft.key in answered_keys:
                problems.append(
                    f"{rule}: key '{draft.key}' is a rule from the person's answer to a "
                    "clarification. Connexity carries it over unchanged; leave it out. "
                    "To change it, raise a clarification that replaces it."
                )
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
                critical=d.critical,
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
            carried=len(answered_keys),
            quotes_checked=text is not None,
        ),
    )


def mark_critical_rules(
    *,
    session: Session,
    agent: Agent,
    critical: Sequence[str],
    not_critical: Sequence[str],
    author: User,
    assistant_name: str | None,
) -> tuple[SpecPublic, int]:
    """Mark rules of the agent's latest spec critical or not, as a new spec version.

    Returns:
        The spec as it now is, and how many rules changed. When none changed, no
        version is made.

    Raises:
        SpecRefused: The agent has no spec, or a key is unknown or in both lists;
            every problem is listed.
    """
    if not critical and not not_critical:
        raise SpecRefused("Name at least one rule key", [])
    lock_agent(session=session, agent_id=agent.id)
    latest = crud.latest_spec(session=session, agent_id=agent.id)
    if latest is None:
        session.rollback()
        raise SpecRefused(
            "The agent has no spec yet",
            ["Write it with `write_spec`, marking critical rules as you write them."],
        )
    rules = {r.key: r for r in crud.spec_rules(session=session, spec_id=latest.id)}
    problems: list[str] = []
    for key in sorted(set(critical) & set(not_critical)):
        problems.append(f"Key '{key}' is in both lists.")
    for key in dict.fromkeys([*critical, *not_critical]):
        if key not in rules:
            problems.append(
                f"Key '{key}' is not a rule of spec version {latest.version}; use the "
                "keys `get_spec` answers."
            )
    if problems:
        session.rollback()
        raise SpecRefused("No rule was marked", problems)
    marks = {key: True for key in critical} | {key: False for key in not_critical}
    changed = sum(1 for key, mark in marks.items() if rules[key].critical != mark)
    if changed:
        mark_critical(
            session=session,
            agent=agent,
            previous=latest,
            rules=list(rules.values()),
            marks=marks,
            author=author,
            assistant_name=assistant_name,
        )
    else:
        session.rollback()
    answer = spec_answer(session=session, agent=agent)
    assert answer is not None
    return answer, changed


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
