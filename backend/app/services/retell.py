import httpx
from fastapi import HTTPException
from pydantic import BaseModel


class RetellAgentSummary(BaseModel):
    agent_id: str
    agent_name: str | None = None
    is_published: bool = False
    version: int | None = None


class RetellDeployResult(BaseModel):
    success: bool
    retell_version_name: str | None = None
    error_message: str | None = None


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


async def deploy_retell_agent(
    *,
    api_key: str,
    retell_agent_id: str,
    connexity_agent_version: int,
    connexity_deployment_id: str,
) -> RetellDeployResult:
    """Patch a Retell agent's metadata to record the Connexity deployment.

    Sends only the metadata field — does not modify Retell's version_title or
    description. Retell creates a new version on update; we read its
    ``version_title`` (falling back to ``v{version}``) for display.
    """
    payload = {
        "metadata": {
            "connexity_agent_version": connexity_agent_version,
            "connexity_deployment_id": connexity_deployment_id,
        }
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://api.retellai.com/update-agent/{retell_agent_id}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
    except httpx.HTTPError as exc:
        return RetellDeployResult(
            success=False,
            error_message=f"Failed to reach Retell API: {exc}",
        )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        return RetellDeployResult(
            success=False,
            error_message=f"Retell update-agent returned {response.status_code}: {detail}",
        )

    try:
        body = response.json()
    except ValueError:
        body = {}

    version_title = body.get("version_title") if isinstance(body, dict) else None
    version_number = body.get("version") if isinstance(body, dict) else None
    if version_title:
        retell_version_name: str | None = str(version_title)
    elif version_number is not None:
        retell_version_name = f"v{version_number}"
    else:
        retell_version_name = None

    return RetellDeployResult(success=True, retell_version_name=retell_version_name)
