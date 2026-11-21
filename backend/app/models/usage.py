"""What a workspace used, counted in units.

One row per real call (observed minutes) and per simulated call (simulated caller
messages). Rows keep units, never dollars: the list price is applied on reading
(`app/services/usage.py`), so a price can change without touching history. A row
outlives the call it came from.

Each row also carries what the models behind it cost Connexity, with the token counts
that cost was worked out from. That part is never returned by a workspace route.
"""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import DateTime, Index, UniqueConstraint, text
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import UsageMeter


class UsageRecord(SQLModel, table=True):
    __tablename__ = "usage_record"
    __table_args__ = (
        UniqueConstraint("source_key", name="uq_usage_record_source_key"),
        Index("ix_usage_record_company_occurred", "company_id", "occurred_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True)
    meter: UsageMeter = Field(sa_type=enum_type(UsageMeter))
    quantity: int
    occurred_at: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    # What the row was counted from: "call:<id>" or "simulated:<id>". It stays when
    # the call itself is deleted, so nothing is counted twice or lost.
    source_key: str = Field(max_length=64)
    call_id: uuid.UUID | None = Field(
        default=None, foreign_key="call.id", index=True, ondelete="SET NULL"
    )
    test_case_result_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="test_case_result.id",
        index=True,
        ondelete="SET NULL",
    )
    run_id: uuid.UUID | None = Field(
        default=None, foreign_key="run.id", index=True, ondelete="SET NULL"
    )
    # Connexity's own cost for this row: the simulated caller and the judge for a
    # simulated call, model checks for a real call. Tokens as the provider reported
    # them, so the cost can be worked out again at another price.
    own_cost_usd: float = 0.0
    model: str = Field(default="", max_length=128)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )


class UsageLinePublic(BaseModel):
    """One meter over the period."""

    meter: UsageMeter
    unit: str = PydanticField(description="What one unit is, in words")
    quantity: int
    unit_price_usd: float = PydanticField(description="List price of one unit")
    cost_usd: float = PydanticField(description="quantity times the list price")


class UsageAgentPublic(BaseModel):
    agent_id: uuid.UUID
    name: str
    lines: list[UsageLinePublic]
    cost_usd: float


class UsageRunPublic(BaseModel):
    """One test run's usage in the period."""

    run_id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    set_name: str | None = None
    started_at: datetime
    simulated_calls: int
    caller_messages: int
    cost_usd: float


class UsageMoverPublic(BaseModel):
    """One of the things that added most to the period's cost."""

    kind: str = PydanticField(
        description="'run' or 'calls' (an agent's real calls on a day)"
    )
    line: str = PydanticField(description="It in one sentence, with units and dollars")
    agent_id: uuid.UUID
    run_id: uuid.UUID | None = None
    day: str | None = PydanticField(default=None, description="For calls: the UTC day")
    quantity: int
    cost_usd: float


class UsagePublic(BaseModel):
    """A workspace's usage over a period, at list price. Nothing is billed."""

    period: str = PydanticField(description="'month', '7d' or '30d'")
    starts_at: datetime
    ends_at: datetime = PydanticField(description="Exclusive")
    agent_id: uuid.UUID | None = None
    lines: list[UsageLinePublic]
    cost_usd: float = PydanticField(description="Every meter together, at list price")
    agents: list[UsageAgentPublic]
    runs: list[UsageRunPublic] = PydanticField(
        description="Runs with usage in the period, most expensive first; paged"
    )
    movers: list[UsageMoverPublic] = PydanticField(
        description="The three things that added most to the cost"
    )
