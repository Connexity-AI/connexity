"""What the Agents page answers (`app/services/agent_list.py`)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import Platform
from app.models.spec import SpecState

AgentType = Literal["single_prompt", "conversational_flow"]
Period = Literal["7d", "30d", "90d"]


class AgentListItemPublic(BaseModel):
    id: uuid.UUID
    name: str
    platform: Platform | None = None
    type: AgentType | None = Field(
        default=None,
        description="From its current version in Connexity's catalogue; None if unknown",
    )
    calls: int = Field(description="Calls in the period")
    spec: SpecState = Field(description="none, current, or needs_review")


class AgentListPublic(BaseModel):
    data: list[AgentListItemPublic] = Field(
        description="Most calls first, then by name"
    )
    period: Period
    synced_at: datetime | None = Field(
        default=None,
        description="When calls were last pulled for the workspace's Retell accounts",
    )
