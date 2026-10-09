"""Read-only reads of a Retell agent at one of its versions.

Separate from ``app.services.retell``, which serves the frozen eval stack and raises
HTTP errors: these raise ``RetellReadError`` so a caller can carry on without them.
"""

from typing import Any

import httpx

_BASE_URL = "https://api.retellai.com"
# Short: a version is read while a webhook waits, and Retell gives a webhook ten
# seconds. A version that could not be read is resolved later.
_TIMEOUT_SECONDS = 4.0


class RetellReadError(Exception):
    """Retell could not be read: unreachable, refused, or an answer that makes no sense."""


async def _get(api_key: str, path: str, version: str | int | None) -> dict[str, Any]:
    params = {"version": version} if version is not None else None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_BASE_URL}{path}",
                headers={"Authorization": f"Bearer {api_key}"},
                params=params,
                timeout=_TIMEOUT_SECONDS,
            )
    except httpx.HTTPError as exc:
        msg = "Could not reach Retell"
        raise RetellReadError(msg) from exc
    if response.status_code != 200:
        msg = f"Retell answered {response.status_code}"
        raise RetellReadError(msg)
    try:
        body = response.json()
    except ValueError as exc:
        msg = "Retell did not answer with JSON"
        raise RetellReadError(msg) from exc
    if not isinstance(body, dict) or not body:
        msg = "Retell answered in an unexpected shape"
        raise RetellReadError(msg)
    return body


async def get_retell_agent_at_version(
    api_key: str, agent_id: str, version: str | int
) -> dict[str, Any]:
    """The agent's settings at ``version``, including which prompt version it uses."""
    return await _get(api_key, f"/get-agent/{agent_id}", version)


async def get_retell_llm_at_version(
    api_key: str, llm_id: str, version: str | int | None
) -> dict[str, Any]:
    """A single-prompt agent's prompt, tools and model at ``version``."""
    return await _get(api_key, f"/get-retell-llm/{llm_id}", version)


async def get_retell_conversation_flow_at_version(
    api_key: str, flow_id: str, version: str | int | None
) -> dict[str, Any]:
    """A conversation flow's nodes, prompts, tools and model at ``version``."""
    return await _get(api_key, f"/get-conversation-flow/{flow_id}", version)
