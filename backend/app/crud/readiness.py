"""What is set up in a workspace, step by step.

- Assistant connected: a member of the workspace holds a usable assistant connection
  (see `connected_assistants`).
- Voice platform connected: the workspace has a voice platform integration.
- Agents and calls synced, first scan done: not started until "First scan" (roadmap
  feature 10) defines them.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from app.core.config import settings
from app.models.enums import IntegrationProvider
from app.models.integration import Integration
from app.models.oauth import OAuthAuthorizationCode, OAuthClient, OAuthRefreshToken
from app.models.readiness import (
    ReadinessPublic,
    ReadinessStep,
    ReadinessStepKey,
    ReadinessStepState,
)
from app.models.workspace_member import WorkspaceMember

VOICE_PLATFORMS = {
    IntegrationProvider.RETELL: "Retell",
    IntegrationProvider.VAPI: "Vapi",
    IntegrationProvider.ELEVENLABS: "ElevenLabs",
}


def connected_assistants(
    *, session: Session, company_id: uuid.UUID, access_token_minutes: int
) -> list[str]:
    """Names of the assistants the workspace's members have connected, oldest first.

    An assistant is connected while it holds a refresh token that is neither revoked
    nor expired, or an access token that has not expired yet (its authorization code
    was exchanged within the access token's lifetime). Clients that never ask for a
    refresh token count only for that hour.
    """
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


def get_readiness(
    *, session: Session, company_id: uuid.UUID, mcp_url: str | None
) -> ReadinessPublic:
    assistants = connected_assistants(
        session=session,
        company_id=company_id,
        access_token_minutes=settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    platforms = connected_voice_platforms(session=session, company_id=company_id)

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
            state=ReadinessStepState.NOT_STARTED,
        ),
        ReadinessStep(
            key=ReadinessStepKey.FIRST_SCAN,
            name="First scan done",
            state=ReadinessStepState.NOT_STARTED,
        ),
    ]
    done = sum(step.state == ReadinessStepState.DONE for step in steps)
    command = (
        f"claude mcp add --transport http connexity {mcp_url}"
        if mcp_url and not assistants
        else None
    )
    return ReadinessPublic(
        steps=steps,
        done=done,
        total=len(steps),
        percent=round(done / len(steps) * 100),
        first_scan_done=False,
        connect_command=command,
    )
