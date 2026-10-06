import httpx


def _vapi_openapi_response(*providers: str) -> httpx.Response:
    payload = {
        "components": {
            "schemas": {
                "CreateAssistantModel": {
                    "properties": {
                        "model": {
                            "properties": {
                                "provider": {"enum": list(providers)},
                            }
                        }
                    }
                }
            }
        }
    }
    return httpx.Response(
        status_code=200,
        json=payload,
        request=httpx.Request("GET", "https://api.vapi.ai/api-json"),
    )
