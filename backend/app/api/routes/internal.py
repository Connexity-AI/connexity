from datetime import timedelta
from hmac import compare_digest

from fastapi import APIRouter, HTTPException, status

from app.core import security
from app.core.config import settings
from app.models import McpServiceToken, McpServiceTokenRequest

SERVICE_TOKEN_EXPIRES_IN_SECONDS = 300

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/token", response_model=McpServiceToken)
def issue_mcp_service_token(body: McpServiceTokenRequest) -> McpServiceToken:
    expected_client_id = settings.resolved_mcp_client_id
    expected_client_secret = (settings.MCP_CLIENT_SECRET or "").strip()
    provided_client_id = body.client_id.strip()
    provided_client_secret = body.client_secret.strip()

    if (
        not expected_client_secret
        or not provided_client_id
        or not provided_client_secret
        or not compare_digest(provided_client_id, expected_client_id)
        or not compare_digest(provided_client_secret, expected_client_secret)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    access_token = security.create_access_token(
        expected_client_id,
        timedelta(seconds=SERVICE_TOKEN_EXPIRES_IN_SECONDS),
        additional_claims={"typ": "service", "scope": "mcp:actions"},
    )
    return McpServiceToken(
        access_token=access_token,
        expires_in=SERVICE_TOKEN_EXPIRES_IN_SECONDS,
    )
