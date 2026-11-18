"""The onboarding steps as the public `/mcp-docs` page shows them."""

from typing import Literal

from pydantic import BaseModel, Field


class OnboardingStepPublic(BaseModel):
    key: str
    title: str
    who: Literal["person", "assistant"] = Field(description="Who acts on the step")
    done_when: str = Field(description="When it counts as done, in one sentence")
    instructions: list[str] = Field(
        description=(
            "What the assistant does, in order. A tool is written `like_this`; a guide "
            "as [[name]], for connexity://guides/name."
        )
    )
