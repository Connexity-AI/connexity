"""Work out which version of each component served a call, and keep each version once.

Voice side (Retell): a call carries the agent's version number. The first time a
version is seen, it is read from Retell and recorded as three components: the agent's
settings, its prompt, and its model. Skill side (n8n): an execution carries the
workflow as it ran, which is recorded when the execution is copied.

A provider that cannot be read never stops a call from being stored.
"""

import logging
import time
import uuid
from typing import Any

from sqlmodel import Session, col, delete, select

from app import crud
from app.core.encryption import decrypt
from app.models.agent import Agent
from app.models.call import Call, CallComponent
from app.models.component_version import (
    STATE_KINDS,
    ComponentVersion,
    ServedBy,
    VersionResolveResult,
)
from app.models.enums import Platform
from app.models.execution import CallExecution
from app.models.integration import Integration
from app.models.trace import Trace, TraceComponent
from app.services.fingerprint import (
    combined_fingerprint,
    fingerprint,
    mask_secrets,
    without,
)
from app.services.n8n import N8nError, get_n8n_execution
from app.services.retell_versions import (
    RetellReadError,
    get_retell_agent_at_version,
    get_retell_conversation_flow_at_version,
    get_retell_llm_at_version,
)

logger = logging.getLogger(__name__)

# Fields that change without the content changing. Left out of a fingerprint.
_VOLATILE = (
    "version",
    "base_version",
    "is_published",
    "version_title",
    "last_modification_timestamp",
)
# The agent's link to its prompt is its own component, not part of its settings.
_AGENT_NOT_SETTINGS = (*_VOLATILE, "response_engine")
_MODEL_FIELDS = ("model", "model_temperature", "model_high_priority", "model_choice")
_PROMPT_NOT_CONTENT = (*_VOLATILE, *_MODEL_FIELDS)
# Where a node sits on the canvas is not what the workflow does.
_NODE_NOT_CONTENT = ("position",)

SKILL_PROVIDER = "n8n"


def _link(kind: str, ref: str, version: str) -> dict[str, str]:
    return {"kind": kind, "ref": ref, "version": version}


def _as_component(row: ComponentVersion) -> TraceComponent:
    return TraceComponent(
        kind=row.kind,
        name=row.name,
        ref=row.ref,
        version=row.version or None,
        fingerprint=row.fingerprint,
    )


def _model_of(prompt: dict[str, Any]) -> dict[str, Any]:
    return {key: prompt[key] for key in _MODEL_FIELDS if prompt.get(key) is not None}


def _model_name(model: dict[str, Any]) -> str | None:
    name = model.get("model")
    choice = model.get("model_choice")
    if not name and isinstance(choice, dict):
        name = choice.get("model")
    return str(name) if name else None


async def _read_retell_version(
    *,
    session: Session,
    agent: Agent,
    api_key: str,
    provider_agent_id: str,
    version: str,
) -> ComponentVersion:
    """Read one agent version from Retell and record its components."""
    settings = await get_retell_agent_at_version(api_key, provider_agent_id, version)
    engine = settings.get("response_engine")
    engine = engine if isinstance(engine, dict) else {}
    engine_type = engine.get("type")
    engine_version = engine.get("version")
    links: list[dict[str, str]] = []

    prompt: dict[str, Any] | None = None
    prompt_kind, prompt_ref = "prompt", None
    if engine_type == "retell-llm" and engine.get("llm_id"):
        prompt_ref = str(engine["llm_id"])
        prompt = await get_retell_llm_at_version(api_key, prompt_ref, engine_version)
    elif engine_type == "conversation-flow" and engine.get("conversation_flow_id"):
        prompt_kind, prompt_ref = "flow", str(engine["conversation_flow_id"])
        prompt = await get_retell_conversation_flow_at_version(
            api_key, prompt_ref, engine_version
        )

    if prompt is not None and prompt_ref is not None:
        content = mask_secrets(without(prompt, _PROMPT_NOT_CONTENT))
        # No version named: the content's own hash stands in, so that two different
        # prompts are never filed as one.
        prompt_version = (
            str(engine_version)
            if engine_version is not None
            else fingerprint(content)[:12]
        )
        crud.record_component_version(
            session=session,
            agent_id=agent.id,
            company_id=agent.company_id,
            kind=prompt_kind,
            name="Conversation flow" if prompt_kind == "flow" else "Prompt",
            ref=prompt_ref,
            version=prompt_version,
            fingerprint=fingerprint(content),
            content=content,
        )
        links.append(_link(prompt_kind, prompt_ref, prompt_version))

        model = _model_of(prompt)
        model_name = _model_name(model)
        if model_name:
            crud.record_component_version(
                session=session,
                agent_id=agent.id,
                company_id=agent.company_id,
                kind="model",
                name=model_name,
                ref=model_name,
                # A model has no version of its own; its settings tell two uses apart.
                version=fingerprint(model)[:12],
                fingerprint=fingerprint(model),
                content=model,
            )
            links.append(_link("model", model_name, fingerprint(model)[:12]))

    content = mask_secrets(without(settings, _AGENT_NOT_SETTINGS))
    row, _created = crud.record_component_version(
        session=session,
        agent_id=agent.id,
        company_id=agent.company_id,
        kind="agent",
        name=str(settings.get("agent_name") or provider_agent_id),
        ref=provider_agent_id,
        version=version,
        fingerprint=fingerprint(content),
        content=content,
        links=links,
    )
    return row


def _components_from_catalogue(
    *, session: Session, agent: Agent, agent_row: ComponentVersion
) -> list[TraceComponent]:
    components = [_as_component(agent_row)]
    for link in agent_row.links or []:
        linked = crud.get_component_version(
            session=session,
            agent_id=agent.id,
            kind=link["kind"],
            ref=link["ref"],
            version=link["version"],
        )
        if linked is not None:
            component = _as_component(linked)
            if linked.kind == "model":
                component.version = None
            components.append(component)
    return components


async def retell_components(
    *,
    session: Session,
    agent: Agent,
    api_key: str,
    provider_agent_id: str,
    version: str,
) -> tuple[list[TraceComponent], bool]:
    """What served a call on ``version`` of a Retell agent.

    Reads Retell only the first time a version is seen.

    Returns:
        The components, and whether Retell was read.

    Raises:
        RetellReadError: The version is not in the catalogue and Retell cannot be read.
    """
    row = crud.get_component_version(
        session=session,
        agent_id=agent.id,
        kind="agent",
        ref=provider_agent_id,
        version=version,
    )
    read = row is None
    if row is None:
        row = await _read_retell_version(
            session=session,
            agent=agent,
            api_key=api_key,
            provider_agent_id=provider_agent_id,
            version=version,
        )
    return (
        _components_from_catalogue(session=session, agent=agent, agent_row=row),
        read,
    )


async def add_retell_components(
    *, session: Session, agent: Agent, api_key: str, trace: Trace
) -> Trace:
    """``trace`` with its agent component replaced by agent, prompt and model.

    Never raises: when the version cannot be resolved the trace is returned unchanged,
    and the agent's stored calls can be resolved later.
    """
    agent_component = next(
        (c for c in trace.components or [] if c.kind == "agent"), None
    )
    if (
        agent_component is None
        or not agent_component.ref
        or not agent_component.version
    ):
        return trace
    try:
        resolved, _read = await retell_components(
            session=session,
            agent=agent,
            api_key=api_key,
            provider_agent_id=agent_component.ref,
            version=agent_component.version,
        )
    except RetellReadError as exc:
        logger.warning(
            "Version %s of agent %s could not be read: %s",
            agent_component.version,
            agent.id,
            exc,
        )
        return trace
    except Exception:  # noqa: BLE001 - a call is stored whether or not this works
        session.rollback()
        logger.exception("Version of agent %s could not be resolved", agent.id)
        return trace
    others = [c for c in trace.components or [] if c.kind not in STATE_KINDS]
    return trace.model_copy(update={"components": [*resolved, *others]})


# ── Skills ─────────────────────────────────────────────────────────


def record_skill_version(
    *, session: Session, call: Call, payload: dict[str, Any]
) -> tuple[str, bool] | None:
    """Record the workflow an n8n execution carried.

    n8n can only return a workflow's current version, so the copy inside an execution
    is the only record of what ran.

    Returns:
        The version it is filed under and whether it was new; ``None`` when the
        execution carries no workflow.
    """
    workflow = payload.get("workflowData")
    workflow_id = payload.get("workflowId")
    if not isinstance(workflow, dict) or workflow_id is None:
        return None
    nodes = [
        without(node, _NODE_NOT_CONTENT)
        for node in workflow.get("nodes") or []
        if isinstance(node, dict)
    ]
    content = mask_secrets(
        {
            "nodes": sorted(nodes, key=lambda node: str(node.get("name"))),
            "connections": workflow.get("connections"),
            "settings": workflow.get("settings"),
        }
    )
    digest = fingerprint(content)
    # An n8n too old to report a version id: the content's own hash stands in.
    version = str(payload.get("workflowVersionId") or digest[:12])
    _row, created = crud.record_component_version(
        session=session,
        agent_id=call.agent_id,
        company_id=call.company_id,
        kind="skill",
        name=str(workflow.get("name") or workflow_id),
        ref=str(workflow_id),
        version=version,
        fingerprint=digest,
        content=content,
    )
    return version, created


def served_by(*, session: Session, call: Call, trace: Trace) -> list[ServedBy]:
    """What served ``call``: the trace's components, and a skill per workflow that ran."""
    rows = crud.list_component_versions(session=session, agent_id=call.agent_id)
    by_version = {(row.kind, row.ref, row.version): row for row in rows}
    # A model has no version of its own; it is found by its fingerprint.
    by_fingerprint = {(row.kind, row.ref, row.fingerprint): row for row in rows}
    listed: list[ServedBy] = []
    for component in trace.components or []:
        ref = component.ref or ""
        row = by_version.get((component.kind, ref, component.version or "")) or (
            by_fingerprint.get((component.kind, ref, component.fingerprint or ""))
        )
        listed.append(
            ServedBy(
                kind=component.kind,
                name=component.name,
                ref=component.ref,
                version=component.version,
                fingerprint=component.fingerprint,
                component_version_id=row.id if row else None,
            )
        )

    skills = {(row.ref, row.version): row for row in rows if row.kind == "skill"}
    seen: set[tuple[str, str | None]] = set()
    for execution in session.exec(
        select(CallExecution)
        .where(CallExecution.call_id == call.id)
        .order_by(col(CallExecution.started_at))
    ).all():
        key = (execution.workflow_id or "", execution.workflow_version)
        if not execution.workflow_id or key in seen:
            continue
        seen.add(key)
        row = skills.get((execution.workflow_id, execution.workflow_version or ""))
        listed.append(
            ServedBy(
                kind="skill",
                name=execution.workflow_name or execution.workflow_id,
                ref=execution.workflow_id,
                version=execution.workflow_version,
                fingerprint=row.fingerprint if row else None,
                component_version_id=row.id if row else None,
            )
        )
    return listed


# ── Stored calls ───────────────────────────────────────────────────


def _apply(session: Session, call: Call, components: list[TraceComponent]) -> None:
    """Replace the state components of a stored call, keeping any others it has."""
    kept = [
        row
        for row in session.exec(
            select(CallComponent)
            .where(CallComponent.call_id == call.id)
            .order_by(col(CallComponent.seq))
        ).all()
        if row.kind not in STATE_KINDS
    ]
    others = [
        TraceComponent(
            kind=row.kind,
            name=row.name,
            ref=row.ref,
            version=row.version,
            fingerprint=row.fingerprint,
        )
        for row in kept
    ]
    session.exec(delete(CallComponent).where(col(CallComponent.call_id) == call.id))
    session.flush()
    for seq, component in enumerate([*components, *others]):
        session.add(
            CallComponent(
                company_id=call.company_id,
                call_id=call.id,
                seq=seq,
                kind=component.kind,
                name=component.name,
                ref=component.ref,
                version=component.version,
                fingerprint=component.fingerprint,
            )
        )
    call.agent_version = components[0].version if components else call.agent_version
    call.state_fingerprint = combined_fingerprint(
        {c.kind: c.fingerprint for c in components if c.fingerprint}
    )
    session.add(call)


async def resolve_agent_versions(
    *, session: Session, agent: Agent
) -> VersionResolveResult:
    """Resolve what served the agent's stored calls. Safe to run again.

    Each agent version is read from the provider once. A workflow version is recorded
    for each stored execution the backend still holds.
    """
    result = VersionResolveResult(
        calls_resolved=0, calls_unresolved=0, versions_read=0, skills_recorded=0
    )
    problems: set[str] = set()

    if agent.platform == Platform.RETELL and agent.integration_id is not None:
        integration = session.get(Integration, agent.integration_id)
        api_key = decrypt(integration.encrypted_api_key) if integration else None
        pending = session.exec(
            select(Call, CallComponent)
            .join(CallComponent, col(CallComponent.call_id) == col(Call.id))
            .where(
                Call.agent_id == agent.id,
                col(Call.deleted_at).is_(None),
                col(Call.state_fingerprint).is_(None),
                CallComponent.kind == "agent",
            )
        ).all()
        resolved: dict[tuple[str, str], list[TraceComponent] | None] = {}
        for call, component in pending:
            if not component.ref or not component.version or api_key is None:
                result.calls_unresolved += 1
                continue
            key = (component.ref, component.version)
            if key not in resolved:
                try:
                    components, read = await retell_components(
                        session=session,
                        agent=agent,
                        api_key=api_key,
                        provider_agent_id=component.ref,
                        version=component.version,
                    )
                    result.versions_read += int(read)
                    resolved[key] = components
                except RetellReadError as exc:
                    problems.add(f"version {component.version}: {exc}")
                    resolved[key] = None
            components_for_call = resolved[key]
            if components_for_call is None:
                result.calls_unresolved += 1
                continue
            _apply(session, call, components_for_call)
            result.calls_resolved += 1
        session.commit()

    result.skills_recorded = await _record_missing_skills(
        session=session, agent_id=agent.id, problems=problems
    )
    result.problems = sorted(problems)
    return result


async def _record_missing_skills(
    *, session: Session, agent_id: uuid.UUID, problems: set[str]
) -> int:
    known = {
        (row.ref, row.version)
        for row in crud.list_component_versions(
            session=session, agent_id=agent_id, kind="skill"
        )
    }
    recorded = 0
    executions = session.exec(
        select(CallExecution, Call)
        .join(Call, col(Call.id) == col(CallExecution.call_id))
        .where(
            Call.agent_id == agent_id,
            CallExecution.provider == SKILL_PROVIDER,
            col(CallExecution.integration_id).is_not(None),
        )
        .order_by(col(CallExecution.started_at))
    ).all()
    integrations: dict[uuid.UUID, Integration | None] = {}
    for execution, call in executions:
        key = (execution.workflow_id or "", execution.workflow_version or "")
        if key in known or execution.integration_id is None:
            continue
        # One read per missing version, whether or not it succeeds.
        known.add(key)
        if execution.integration_id not in integrations:
            integrations[execution.integration_id] = session.get(
                Integration, execution.integration_id
            )
        integration = integrations[execution.integration_id]
        if integration is None:
            continue
        try:
            payload = await get_n8n_execution(
                integration.base_url or "",
                decrypt(integration.encrypted_api_key),
                execution.external_id,
            )
        except N8nError as exc:
            problems.add(f"{integration.name}: {exc}")
            continue
        skill = record_skill_version(session=session, call=call, payload=payload)
        if skill is None:
            continue
        version, created = skill
        recorded += int(created)
        if execution.workflow_version != version:
            # Filed under the content's hash: the execution must point at the same.
            execution.workflow_version = version
            session.add(execution)
            session.commit()
    return recorded


# ── Without being asked ────────────────────────────────────────────

# After a pass that left something unresolved (a version the provider no longer has, a
# provider that is down), the next automatic pass for that agent waits this long. Kept
# in this process only: another worker may try once more, which is harmless.
_RETRY_AFTER_SECONDS = 600.0
_retry_not_before: dict[uuid.UUID, float] = {}


def has_unresolved_versions(*, session: Session, agent_id: uuid.UUID) -> bool:
    """Whether any stored call of the agent names an agent version but no state yet."""
    return (
        session.exec(
            select(Call.id)
            .join(CallComponent, col(CallComponent.call_id) == col(Call.id))
            .where(
                Call.agent_id == agent_id,
                col(Call.deleted_at).is_(None),
                col(Call.state_fingerprint).is_(None),
                CallComponent.kind == "agent",
                col(CallComponent.version).is_not(None),
            )
            .limit(1)
        ).first()
        is not None
    )


async def resolve_agent_versions_quietly(*, session: Session, agent: Agent) -> None:
    """Resolve the agent's stored calls as part of background work. Never raises.

    Does nothing when every call is resolved, or when a recent pass could not finish.
    """
    now = time.monotonic()
    if _retry_not_before.get(agent.id, 0.0) > now:
        return
    try:
        if not has_unresolved_versions(session=session, agent_id=agent.id):
            return
        result = await resolve_agent_versions(session=session, agent=agent)
    except Exception:  # noqa: BLE001 - background work has no one to raise to
        session.rollback()
        logger.exception("Versions of agent %s could not be resolved", agent.id)
        _retry_not_before[agent.id] = now + _RETRY_AFTER_SECONDS
        return
    if result.calls_unresolved or result.problems:
        _retry_not_before[agent.id] = now + _RETRY_AFTER_SECONDS
        logger.warning(
            "Versions of agent %s: %d call(s) unresolved: %s",
            agent.id,
            result.calls_unresolved,
            "; ".join(result.problems),
        )
