"""The fixed categories every issue (and later every spec rule) belongs to.

One Connexity-wide set, the same for every workspace, so it carries no `company_id`.
The Connexity team edits names and order in the database; code refers to a category by
its `key`, which never changes once seeded (Decided 2026-11-12). See
`plans/2026-11-13-categories-table.md`.
"""

import uuid

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import CategoryKind


class Category(SQLModel, table=True):
    __tablename__ = "category"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key: str = Field(max_length=64, unique=True)
    name: str = Field(max_length=255)
    # The fixed order. Not unique, so two categories can swap places in one edit; ties
    # fall back to the key.
    position: int
    kind: CategoryKind = Field(sa_type=enum_type(CategoryKind))


class CategoryPublic(BaseModel):
    key: str
    name: str
    position: int
    kind: CategoryKind


# The 14 categories of design prompt 06, in order. The migration seeds them; the names
# here are only the first ones, since the team may rename a category later.
SEED: list[tuple[str, str, CategoryKind]] = [
    (
        "greeting_and_identification",
        "Greeting and identification",
        CategoryKind.BEHAVIOUR,
    ),
    ("information_collection", "Information collection", CategoryKind.BEHAVIOUR),
    ("booking", "Booking", CategoryKind.BEHAVIOUR),
    (
        "rescheduling_and_cancelling",
        "Rescheduling and cancelling",
        CategoryKind.BEHAVIOUR,
    ),
    ("pricing_and_quotes", "Pricing and quotes", CategoryKind.BEHAVIOUR),
    ("objection_handling", "Objection handling", CategoryKind.BEHAVIOUR),
    ("transfers_and_escalation", "Transfers and escalation", CategoryKind.BEHAVIOUR),
    ("compliance_and_privacy", "Compliance and privacy", CategoryKind.BEHAVIOUR),
    ("conversation_flow_quality", "Conversation flow quality", CategoryKind.BEHAVIOUR),
    ("ending_the_call", "Ending the call", CategoryKind.BEHAVIOUR),
    ("responsiveness", "Responsiveness", CategoryKind.TECHNICAL),
    ("tools_and_integrations", "Tools and integrations", CategoryKind.TECHNICAL),
    ("speech_recognition", "Speech recognition", CategoryKind.TECHNICAL),
    ("other", "Other", CategoryKind.BEHAVIOUR),
]
OTHER = "other"
