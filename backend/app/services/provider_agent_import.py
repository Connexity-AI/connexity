"""Import simulator fields from Retell, Vapi, or ElevenLabs for new agents."""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlmodel import Session

from app import crud
from app.core.encryption import decrypt
from app.models import AgentCreateDraft
from app.models.enums import AgentPromptType, IntegrationProvider, Platform
from app.models.imported_platform_config import ImportedPlatformConfig

logger = logging.getLogger(__name__)


def _is_non_blocking_retell_import_error(exc: HTTPException) -> bool:
    if exc.status_code != 422:
        return False
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return (
        detail == "Retell agent has no associated LLM (response_engine.llm_id missing)"
        or "Retell LLM is missing general_prompt or model" in detail
    )


def _provider_for_platform(platform: Platform) -> IntegrationProvider:
    if platform == Platform.RETELL:
        return IntegrationProvider.RETELL
    if platform == Platform.VAPI:
        return IntegrationProvider.VAPI
    if platform == Platform.ELEVENLABS:
        return IntegrationProvider.ELEVENLABS
    msg = f"Platform {platform} does not use integrations"
    raise ValueError(msg)


async def import_config_for_new_agent(
    *, session: Session, body: AgentCreateDraft
) -> ImportedPlatformConfig | None:
    if body.prompt_type == AgentPromptType.MULTI_PROMPT:
        raise HTTPException(
            status_code=422, detail="Multi prompt mode is not available yet"
        )
    if body.platform is None:
        return None
    if body.platform == Platform.WEBHOOK:
        return None
    if body.integration_id is None or not body.platform_agent_id:
        raise HTTPException(
            status_code=422,
            detail="integration_id and platform_agent_id are required for provider agents",
        )

    integration = crud.get_integration(
        session=session, integration_id=body.integration_id
    )
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    expected = _provider_for_platform(body.platform)
    if integration.provider != expected:
        raise HTTPException(
            status_code=422,
            detail="Integration provider does not match selected platform",
        )

    api_key = decrypt(integration.encrypted_api_key)

    if body.platform == Platform.RETELL:
        from app.services.retell import import_retell_agent_config

        try:
            return await import_retell_agent_config(
                api_key=api_key, retell_agent_id=body.platform_agent_id
            )
        except HTTPException as exc:
            if not _is_non_blocking_retell_import_error(exc):
                raise
            logger.info(
                "Skipping Retell config import for new agent retell_agent_id=%s: %s",
                body.platform_agent_id,
                exc.detail,
            )
            return None
    if body.platform == Platform.VAPI:
        from app.services.vapi import import_vapi_assistant_config

        return await import_vapi_assistant_config(
            api_key=api_key, assistant_id=body.platform_agent_id
        )
    if body.platform == Platform.ELEVENLABS:
        from app.services.elevenlabs import import_elevenlabs_agent_config

        return await import_elevenlabs_agent_config(
            api_key=api_key, agent_id=body.platform_agent_id
        )

    raise HTTPException(status_code=422, detail="Unsupported platform for import")
