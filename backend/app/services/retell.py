import httpx
from fastapi import HTTPException
from pydantic import BaseModel


class RetellAgentSummary(BaseModel):
    agent_id: str
    agent_name: str | None = None
    is_published: bool = False
    version: int | None = None


async def test_retell_connection(api_key: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.retellai.com/list-agents",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def list_retell_agents(api_key: str) -> list[RetellAgentSummary]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.retellai.com/list-agents",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach Retell API"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Retell API returned an error")

    agents: list[RetellAgentSummary] = []
    for item in response.json():
        agents.append(
            RetellAgentSummary(
                agent_id=item.get("agent_id", ""),
                agent_name=item.get("agent_name"),
                is_published=bool(item.get("is_published", False)),
                version=item.get("version"),
            )
        )
    return agents
