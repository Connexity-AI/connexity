"""What is set up in a workspace, step by step.

- Assistant connected: a member of the workspace holds a usable assistant connection,
  OAuth or a personal access token (see `connected_assistants`).
- Voice platform connected: the workspace has a voice platform integration.
- Agents and calls synced: in progress once agents linked to a voice platform are added;
  done once every added Retell agent's first scan has finished.
- First scan done: done the first time step 3 is done, and stays done when agents are
  added later (`Company.first_scan_done_at`).
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, func, select

from app.core.config import settings
from app.models.agent import Agent
from app.models.call import Call
from app.models.company import Company
from app.models.enums import IntegrationProvider, Platform
from app.models.integration import Integration
from app.models.oauth import OAuthAuthorizationCode, OAuthClient, OAuthRefreshToken
from app.models.readiness import (
    ReadinessPublic,
    ReadinessStep,
    ReadinessStepKey,
    ReadinessStepState,
)
from app.models.workspace_member import WorkspaceMember
from app.services.connections import VOICE_PLATFORMS


def connected_assistants(
    *, session: Session, company_id: uuid.UUID, access_token_minutes: int
) -> list[str]:
    """Names of the assistants the workspace's members have connected, oldest first.

    An assistant is connected while it holds a refresh token that is neither revoked
    nor expired, or an access token that has not expired yet (its authorization code
    was exchanged within the access token's lifetime). Clients that never ask for a
    refresh token count only for that hour. A personal access token counts from its
    first use until it is revoked.
    """
    from app.crud.personal_access_token import assistants_by_token

    now = datetime.now(UTC)
    members = select(WorkspaceMember.user_id).where(
        WorkspaceMember.company_id == company_id
    )
    found: list[tuple[datetime, str]] = []

    refresh = session.exec(
        select(OAuthRefreshToken, OAuthClient)
        .join(OAuthClient, col(OAuthClient.client_id) == OAuthRefreshToken.client_id)
        .where(
            col(OAuthRefreshToken.user_id).in_(members),
            col(OAuthRefreshToken.revoked_at).is_(None),
            col(OAuthRefreshToken.expires_at) > now,
        )
    ).all()
    for token, client in refresh:
        if _aware(token.expires_at) > now:
            found.append((_aware(token.created_at), _client_name(client)))

    recent = now - timedelta(minutes=access_token_minutes)
    exchanged = session.exec(
        select(OAuthAuthorizationCode, OAuthClient)
        .join(
            OAuthClient, col(OAuthClient.client_id) == OAuthAuthorizationCode.client_id
        )
        .where(
            col(OAuthAuthorizationCode.user_id).in_(members),
            col(OAuthAuthorizationCode.consumed_at) > recent,
        )
    ).all()
    for code, client in exchanged:
        if code.consumed_at is not None and _aware(code.consumed_at) > recent:
            found.append((_aware(code.consumed_at), _client_name(client)))

    found.extend(assistants_by_token(session=session, company_id=company_id))

    names: list[str] = []
    for _, name in sorted(found):
        if name not in names:
            names.append(name)
    return names


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _client_name(client: OAuthClient) -> str:
    return (client.client_name or "").strip() or "An assistant"


def connected_voice_platforms(*, session: Session, company_id: uuid.UUID) -> list[str]:
    providers = session.exec(
        select(Integration.provider)
        .where(
            Integration.company_id == company_id,
            col(Integration.provider).in_(list(VOICE_PLATFORMS)),
        )
        .distinct()
    ).all()
    return sorted(VOICE_PLATFORMS[IntegrationProvider(p)] for p in providers)


def linked_agents(*, session: Session, company_id: uuid.UUID) -> list[Agent]:
    """The workspace's agents linked to a voice platform agent (added to sync)."""
    return list(
        session.exec(
            select(Agent)
            .where(
                Agent.company_id == company_id,
                col(Agent.integration_id).is_not(None),
                col(Agent.platform_agent_id).is_not(None),
            )
            .order_by(col(Agent.created_at))
        ).all()
    )


def synced_call_count(*, session: Session, company_id: uuid.UUID) -> int:
    """Calls stored for the workspace's added agents."""
    linked = select(Agent.id).where(
        Agent.company_id == company_id,
        col(Agent.integration_id).is_not(None),
        col(Agent.platform_agent_id).is_not(None),
    )
    return session.exec(
        select(func.count())
        .select_from(Call)
        .where(
            Call.company_id == company_id,
            col(Call.agent_id).in_(linked),
            col(Call.deleted_at).is_(None),
        )
    ).one()


def _plural(n: int, word: str) -> str:
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def _sync_step(
    *, session: Session, company_id: uuid.UUID, agents: list[Agent]
) -> tuple[ReadinessStepState, str | None]:
    """Step 3's state and detail."""
    if not agents:
        return ReadinessStepState.NOT_STARTED, None
    calls = synced_call_count(session=session, company_id=company_id)
    scanned = [a for a in agents if a.platform == Platform.RETELL]
    finished = [a for a in scanned if a.scan_done_at is not None]
    if scanned and len(finished) == len(scanned):
        return (
            ReadinessStepState.DONE,
            f"{_plural(len(agents), 'agent')} · {_plural(calls, 'call')}",
        )
    started = [a for a in scanned if a.scan_total is not None]
    if not started:
        return (
            ReadinessStepState.IN_PROGRESS,
            f"{_plural(len(agents), 'agent')} · {_plural(calls, 'call')}",
        )
    total = sum(a.scan_total or 0 for a in started)
    stored = sum(stored_in_window(session=session, agent=a) for a in started)
    return (
        ReadinessStepState.IN_PROGRESS,
        f"{min(stored, total):,} of {_plural(total, 'call')} · "
        f"{len(finished)} of {_plural(len(scanned), 'agent')}",
    )


def stored_in_window(*, session: Session, agent: Agent) -> int:
    """Stored calls of the agent inside its first scan's window."""
    if agent.scan_from is None or agent.scan_until is None:
        return 0
    return session.exec(
        select(func.count())
        .select_from(Call)
        .where(
            Call.agent_id == agent.id,
            col(Call.deleted_at).is_(None),
            col(Call.started_at) > _naive(agent.scan_from),
            col(Call.started_at) <= _naive(agent.scan_until),
        )
    ).one()


def _naive(moment: datetime) -> datetime:
    # Call times are stored naive, in UTC.
    return _aware(moment).astimezone(UTC).replace(tzinfo=None)


def calls_without_versions(*, session: Session, company_id: uuid.UUID) -> int:
    """Stored calls of the workspace's added agents whose versions are not resolved."""
    linked = select(Agent.id).where(
        Agent.company_id == company_id,
        col(Agent.integration_id).is_not(None),
        col(Agent.platform_agent_id).is_not(None),
    )
    return session.exec(
        select(func.count())
        .select_from(Call)
        .where(
            Call.company_id == company_id,
            col(Call.agent_id).in_(linked),
            col(Call.deleted_at).is_(None),
            col(Call.state_fingerprint).is_(None),
        )
    ).one()


def get_readiness(
    *, session: Session, company_id: uuid.UUID, mcp_url: str | None
) -> ReadinessPublic:
    assistants = connected_assistants(
        session=session,
        company_id=company_id,
        access_token_minutes=settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    platforms = connected_voice_platforms(session=session, company_id=company_id)
    agents = linked_agents(session=session, company_id=company_id)
    sync_state, sync_detail = _sync_step(
        session=session, company_id=company_id, agents=agents
    )
    company = session.get(Company, company_id)
    # Set by the scan step that finished every agent (`app/services/first_scan.py`).
    first_scan_done = company is not None and company.first_scan_done_at is not None
    scan_detail: str | None = None
    if first_scan_done:
        calls = synced_call_count(session=session, company_id=company_id)
        scan_detail = f"{_plural(calls, 'call')} across {_plural(len(agents), 'agent')}"
        missing = calls_without_versions(session=session, company_id=company_id)
        if missing:
            scan_detail += f" · {_plural(missing, 'call')} without versions"

    def state(done: bool) -> ReadinessStepState:
        return ReadinessStepState.DONE if done else ReadinessStepState.NOT_STARTED

    steps = [
        ReadinessStep(
            key=ReadinessStepKey.ASSISTANT,
            name="Assistant connected",
            state=state(bool(assistants)),
            detail=", ".join(assistants) if assistants else "Not connected yet",
        ),
        ReadinessStep(
            key=ReadinessStepKey.VOICE_PLATFORM,
            name="Voice platform connected",
            state=state(bool(platforms)),
            detail=", ".join(platforms) or None,
        ),
        ReadinessStep(
            key=ReadinessStepKey.SYNC,
            name="Agents and calls synced",
            state=sync_state,
            detail=sync_detail,
        ),
        ReadinessStep(
            key=ReadinessStepKey.FIRST_SCAN,
            name="First scan done",
            state=state(first_scan_done),
            detail=scan_detail,
        ),
    ]
    done = sum(step.state == ReadinessStepState.DONE for step in steps)
    return ReadinessPublic(
        steps=steps,
        done=done,
        total=len(steps),
        percent=round(done / len(steps) * 100),
        first_scan_done=first_scan_done,
        mcp_url=mcp_url,
    )
