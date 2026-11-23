"""What a model provider billed Connexity for a day, beside what Connexity recorded.

One row per day (UTC), provider and model. Billed comes from the provider's own cost
and usage reports for the whole account; recorded is the sum of `usage_record` for the
same day and model. Connexity's own account: no workspace owns a row and no route
returns one. Plan: `plans/2026-11-23-anthropic-cost-comparison.md`.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import BigInteger, DateTime, UniqueConstraint, text
from sqlmodel import Field, SQLModel


class ProviderCostDay(SQLModel, table=True):
    __tablename__ = "provider_cost_day"
    __table_args__ = (
        UniqueConstraint(
            "day", "provider", "model", name="uq_provider_cost_day_day_provider_model"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    day: date
    provider: str = Field(max_length=32)
    # The provider's name for the model; empty for a cost no model is named for.
    model: str = Field(max_length=128)
    billed_usd: float = 0.0
    # Input tokens that were not read from a cache, as the provider counts them.
    billed_input_tokens: int = Field(default=0, sa_type=BigInteger)
    billed_output_tokens: int = Field(default=0, sa_type=BigInteger)
    billed_cache_read_tokens: int = Field(default=0, sa_type=BigInteger)
    billed_cache_write_tokens: int = Field(default=0, sa_type=BigInteger)
    recorded_usd: float = 0.0
    recorded_input_tokens: int = Field(default=0, sa_type=BigInteger)
    recorded_output_tokens: int = Field(default=0, sa_type=BigInteger)
    recorded_cache_read_tokens: int = Field(default=0, sa_type=BigInteger)
    recorded_cache_write_tokens: int = Field(default=0, sa_type=BigInteger)
    read_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )
