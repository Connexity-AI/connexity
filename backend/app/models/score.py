"""The score of an agent or a workspace for a period (`app/services/score.py`)."""

import uuid

from pydantic import BaseModel, Field


class ScoreMovePublic(BaseModel):
    """An issue that costs the score points in the period."""

    issue_id: uuid.UUID
    title: str
    points: float = Field(
        description="How much the score would rise if this issue's findings were gone"
    )
    calls: int = Field(description="Checked calls in the period it was found on")


class ScorePublic(BaseModel):
    score: int | None = Field(
        default=None,
        description=(
            "0 to 100; none before onboarding is complete or with no checked call in "
            "the period"
        ),
    )
    change: int | None = Field(
        default=None,
        description="Against the previous period of the same length; none if either "
        "has no score",
    )
    previous: int | None = Field(
        default=None, description="The score of the previous period of the same length"
    )
    period: str
    checked_calls: int = Field(description="Calls with a result other than unchecked")
    failed_calls: int
    degraded_calls: int
    moves: list[ScoreMovePublic] = Field(
        default_factory=list,
        description="The issues that cost the most points, worst first, up to five",
    )
    why_none: str | None = Field(
        default=None, description="Why there is no score, when there is none"
    )
