"""The onboarding steps, in order, for the public `/mcp-docs` page. No login and no
workspace data: the same list for everyone (`app/services/onboarding.py`)."""

from fastapi import APIRouter

from app.models.onboarding import OnboardingStepPublic
from app.services.onboarding import ONBOARDING_STEPS, for_page

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/steps", response_model=list[OnboardingStepPublic])
def read_onboarding_steps() -> list[OnboardingStepPublic]:
    """The steps a new workspace goes through, in order."""
    return [
        OnboardingStepPublic(
            key=step.key,
            title=step.title,
            who=step.who.value,
            done_when=for_page(step.done_when),
            instructions=[for_page(item.text) for item in step.instructions],
        )
        for step in ONBOARDING_STEPS
    ]
