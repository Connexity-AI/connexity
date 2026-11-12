"""Checking a provider connection before it is stored.

Shared by the web route (`/integrations`) and the MCP route that lets the assistant
connect a voice platform. Connexity only reads from providers; the check is a read.
"""

import uuid
from typing import Literal

from app.core.config import settings
from app.models import IntegrationProvider
from app.services.elevenlabs import check_elevenlabs_connection
from app.services.n8n import check_n8n_connection
from app.services.retell import retell_key_status, test_retell_connection
from app.services.vapi import test_vapi_connection

CONNECTION_TESTERS = {
    IntegrationProvider.RETELL: test_retell_connection,
    IntegrationProvider.VAPI: test_vapi_connection,
    IntegrationProvider.ELEVENLABS: check_elevenlabs_connection,
}

# Voice platforms an assistant may connect, with the name people know them by.
VOICE_PLATFORMS = {
    IntegrationProvider.RETELL: "Retell",
    IntegrationProvider.VAPI: "Vapi",
    IntegrationProvider.ELEVENLABS: "ElevenLabs",
}

# Where each platform's API key is, for the message when a key is refused.
KEY_LOCATION = {
    IntegrationProvider.RETELL: "Retell's dashboard, under API Keys",
    IntegrationProvider.VAPI: "Vapi's dashboard, under Organization › API Keys",
    IntegrationProvider.ELEVENLABS: "ElevenLabs, under Developers › API Keys",
}


async def connection_problem(
    provider: IntegrationProvider, api_key: str, base_url: str | None
) -> str | None:
    """Try the connection. Returns ``None`` when it works, else what went wrong."""
    if provider == IntegrationProvider.N8N:
        if not base_url:
            return "An n8n connection needs the address of the n8n instance"
        result = await check_n8n_connection(base_url, api_key)
        return None if result.ok else result.message
    tester = CONNECTION_TESTERS.get(provider)
    if tester is None or not await tester(api_key):
        return "Could not connect to provider — check your API key and try again"
    return None


async def voice_platform_key_status(
    provider: IntegrationProvider, api_key: str
) -> Literal["ok", "refused", "unreachable"]:
    """Check a voice platform key, telling a refused key from a platform that could
    not be reached. Retell answers precisely; the others only say whether it worked."""
    if provider == IntegrationProvider.RETELL:
        return await retell_key_status(api_key)
    return (
        "ok" if await connection_problem(provider, api_key, None) is None else "refused"
    )


def webhook_address(integration_id: uuid.UUID) -> str:
    """Where the platform sends finished calls for this connection (Retell's webhook)."""
    return (
        f"{settings.oauth_issuer_url}{settings.API_V1_STR}"
        f"/webhooks/retell/{integration_id}"
    )
