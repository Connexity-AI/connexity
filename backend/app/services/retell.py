import httpx


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
