from __future__ import annotations

from connexity_mcp_server.client import ConnexityBackendClient
from connexity_mcp_server.models import (
    AgentDraftResult,
    AgentSummary,
    FindAgentsResult,
    ListAgentsResult,
    UpdateAgentPromptResult,
)

_AGENT_SEARCH_PAGE_SIZE = 100
_AGENT_SEARCH_MAX_PAGES = 10


async def list_agents(
    client: ConnexityBackendClient,
    limit: int = 25,
) -> ListAgentsResult:
    payload = await client.list_agents(skip=0, limit=max(1, min(limit, 100)))
    rows = payload.get("data") if isinstance(payload.get("data"), list) else []
    count = payload.get("count") if isinstance(payload.get("count"), int) else len(rows)
    return ListAgentsResult(
        agents=[_to_agent_summary(row) for row in rows if isinstance(row, dict)],
        count=count,
    )


async def find_agents(
    client: ConnexityBackendClient,
    query: str,
    limit: int = 10,
) -> FindAgentsResult:
    query = query.strip()
    if not query:
        return FindAgentsResult(query=query, agents=[], count=0, message="Query is empty.")

    rows = await _fetch_agents_for_search(client)
    matches = [_to_agent_summary(row) for row in rows if _agent_matches(row, query)]
    matches.sort(key=lambda agent: _agent_sort_key(agent, query))
    limited = matches[: max(1, min(limit, len(matches) if matches else limit))]
    message = None if limited else "No matching agents found."
    return FindAgentsResult(
        query=query,
        agents=limited,
        count=len(matches),
        message=message,
    )


async def get_agent_draft(
    client: ConnexityBackendClient,
    agent_id: str,
) -> AgentDraftResult:
    draft = await client.get_agent_draft(agent_id)
    tools = draft.get("tools") if isinstance(draft.get("tools"), list) else []
    return AgentDraftResult(
        agent_id=agent_id,
        version_id=_string_or_none(draft.get("id")),
        version=_int_or_none(draft.get("version")),
        system_prompt=_string_or_none(draft.get("system_prompt")),
        agent_model=_string_or_none(draft.get("agent_model")),
        agent_provider=_string_or_none(draft.get("agent_provider")),
        agent_temperature=_float_or_none(draft.get("agent_temperature")),
        tools=[tool for tool in tools if isinstance(tool, dict)],
        tools_count=len(tools),
    )


async def update_agent_prompt(
    client: ConnexityBackendClient,
    agent_id: str,
    system_prompt: str,
) -> UpdateAgentPromptResult:
    draft = await client.update_agent_draft(agent_id, system_prompt)
    return UpdateAgentPromptResult(
        agent_id=agent_id,
        version_id=_string_or_none(draft.get("id")),
        version=_int_or_none(draft.get("version")),
        system_prompt=_string_or_none(draft.get("system_prompt")),
        updated=True,
    )


async def _fetch_agents_for_search(client: ConnexityBackendClient) -> list[dict]:
    rows: list[dict] = []
    skip = 0
    total_count = 0

    for _ in range(_AGENT_SEARCH_MAX_PAGES):
        payload = await client.list_agents(skip=skip, limit=_AGENT_SEARCH_PAGE_SIZE)
        page_rows = payload.get("data") if isinstance(payload.get("data"), list) else []
        rows.extend(row for row in page_rows if isinstance(row, dict))
        count = payload.get("count")
        if isinstance(count, int):
            total_count = count
        skip += len(page_rows)
        if not page_rows or (total_count and skip >= total_count):
            break

    return rows


def _to_agent_summary(payload: dict) -> AgentSummary:
    latest = payload.get("latest_published_version")
    latest_version = latest.get("version") if isinstance(latest, dict) else None
    version = latest_version if isinstance(latest_version, int) else None
    has_draft = payload.get("has_draft")
    return AgentSummary(
        id=str(payload.get("id")),
        name=_string_or_none(payload.get("name")),
        description=_string_or_none(payload.get("description")),
        mode=_string_or_none(payload.get("mode")),
        platform=_string_or_none(payload.get("platform")),
        has_draft=bool(has_draft),
        latest_published_version=version,
    )


def _agent_matches(payload: dict, query: str) -> bool:
    haystacks = [
        _string_or_none(payload.get("id")),
        _string_or_none(payload.get("name")),
        _string_or_none(payload.get("description")),
        _string_or_none(payload.get("platform")),
        _string_or_none(payload.get("platform_agent_name")),
    ]
    query_norm = query.casefold()
    return any(text and query_norm in text.casefold() for text in haystacks)


def _agent_sort_key(agent: AgentSummary, query: str) -> tuple[int, str]:
    name = agent.name.casefold() if agent.name else ""
    query_norm = query.casefold()
    return (0 if name.startswith(query_norm) else 1, name)


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _float_or_none(value: object) -> float | None:
    if isinstance(value, (float, int)):
        return float(value)
    return None
