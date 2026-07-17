"""Background extraction of requirements for an agent version.

Version creation is synchronous CRUD; requirement extraction is an async LLM
call. To avoid coupling a slow network call to the version-commit transaction,
routes schedule :func:`extract_requirements_for_version` as a FastAPI
``BackgroundTask`` after they commit. It opens its own session, builds a
``RequirementSource`` from the version (single-prompt or conversation-flow), runs
extraction, and persists the snapshot. Errors are logged, never raised.
"""

import logging
import uuid
from typing import Any

from sqlmodel import Session

from app.core.db import engine
from app.crud import requirement as requirement_crud
from app.models import Agent, AgentVersion
from app.models.enums import RequirementsStatus
from app.services.requirement_extractor import (
    RequirementExtractionError,
    RequirementSource,
    extract_requirements,
)
from app.services.tenant_llm import (
    CompanyMissingLLMKeyError,
    load_tenant_context,
    tenant_scope,
)

logger = logging.getLogger(__name__)


def build_requirement_source(
    *, agent: Agent, version: AgentVersion
) -> RequirementSource:
    """Build the extraction source for a version, handling flow agents.

    Conversation-flow agents carry their flow graph (global prompt, nodes, edges)
    in ``agent.agent_metadata`` (stashed at import); single-prompt agents use the
    version's ``system_prompt``/``tools``.
    """
    metadata: dict[str, Any] = agent.agent_metadata or {}
    is_flow = metadata.get("retell_response_engine") == "conversation-flow"

    if is_flow:
        nodes = metadata.get("conversation_flow_nodes")
        edges = metadata.get("conversation_flow_edges")
        return RequirementSource(
            agent_name=agent.name,
            system_prompt=None,
            tools=version.tools,
            global_prompt=metadata.get("conversation_flow_global_prompt"),
            nodes=nodes if isinstance(nodes, list) else [],
            edges=edges if isinstance(edges, list) else [],
        )

    return RequirementSource(
        agent_name=agent.name,
        system_prompt=version.system_prompt,
        tools=version.tools,
    )


async def extract_requirements_for_version(
    *, agent_id: uuid.UUID, agent_version_id: uuid.UUID
) -> None:
    """Extract and persist requirements for a version in a fresh session.

    Maintains ``requirements_status`` on the version: ``extracting`` while the
    LLM call runs, then ``ready`` (got requirements), ``empty`` (succeeded but
    nothing to extract), or ``failed`` (LLM/parse error — retryable).
    """
    with Session(engine) as session:
        version = session.get(AgentVersion, agent_version_id)
        if version is None:
            logger.warning(
                "Requirement extraction skipped: version %s not found",
                agent_version_id,
            )
            return
        agent = session.get(Agent, agent_id)
        if agent is None:
            logger.warning(
                "Requirement extraction skipped: agent %s not found", agent_id
            )
            return

        requirement_crud.set_requirements_status(
            session=session,
            agent_version_id=agent_version_id,
            status=RequirementsStatus.EXTRACTING,
        )

        # Bind the company's LLM credentials for this extraction. Background
        # tasks run outside any request, so the ambient tenant context that
        # ``call_llm`` reads is not set here — without this, extraction would
        # fall back to the global env key instead of the company's DB key.
        try:
            tenant_ctx = load_tenant_context(
                session=session, company_id=version.company_id
            )
        except CompanyMissingLLMKeyError:
            tenant_ctx = None
            logger.warning(
                "Extracting requirements without tenant LLM context "
                "(no company key) for agent=%s version=%s",
                agent_id,
                agent_version_id,
            )

        source = build_requirement_source(agent=agent, version=version)

        try:
            with tenant_scope(tenant_ctx):
                drafts = await extract_requirements(source=source)
        except RequirementExtractionError:
            logger.exception(
                "Requirement extraction failed for agent=%s version=%s",
                agent_id,
                agent_version_id,
            )
            requirement_crud.set_requirements_status(
                session=session,
                agent_version_id=agent_version_id,
                status=RequirementsStatus.FAILED,
            )
            return

        requirement_crud.replace_requirements_for_version(
            session=session,
            agent_id=agent_id,
            agent_version_id=agent_version_id,
            company_id=version.company_id,
            drafts=drafts,
        )
        requirement_crud.set_requirements_status(
            session=session,
            agent_version_id=agent_version_id,
            status=(RequirementsStatus.READY if drafts else RequirementsStatus.EMPTY),
        )
        logger.info(
            "Extracted %d requirements for agent=%s version=%s (status=%s)",
            len(drafts),
            agent_id,
            agent_version_id,
            "ready" if drafts else "empty",
        )
