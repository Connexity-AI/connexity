from fastapi import APIRouter

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models import ReadinessPublic

router = APIRouter(prefix="/readiness", tags=["readiness"])


@router.get("", response_model=ReadinessPublic)
def read_readiness(session: SessionDep, current_user: CurrentUser) -> ReadinessPublic:
    """Readiness of the workspace open on the web."""
    return crud.get_readiness(
        session=session,
        company_id=current_user.company_id,
        mcp_url=settings.oauth_default_resource_url,
    )
