"""What a model said when a model check (classifier or judge) asked it about a call.

One row per call, check and check version. Checking the call again reads this row
instead of asking again, so a re-check is free and cannot flip a finding by chance. A
new version of the check asks again. The costs add up to the product's daily model
budget (`MODEL_CHECKS_DAILY_BUDGET_USD`).

The answer holds labels and verdicts keyed by event ids, never what a party said.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.check import CHECK_TYPE_MAX_LENGTH
from app.models.columns import enum_type
from app.models.enums import ModelAnswerStatus


class ModelAnswer(SQLModel, table=True):
    __tablename__ = "model_answer"
    __table_args__ = (
        UniqueConstraint(
            "call_id", "check_type", "check_version", name="uq_model_answer_call_check"
        ),
        Index("ix_model_answer_created_at", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    call_id: uuid.UUID = Field(foreign_key="call.id", index=True, ondelete="CASCADE")
    check_type: str = Field(max_length=CHECK_TYPE_MAX_LENGTH)
    check_version: int
    status: ModelAnswerStatus = Field(sa_type=enum_type(ModelAnswerStatus))
    # The provider's versioned model id; empty when the call failed before an answer.
    model: str = Field(default="", max_length=128)
    answer: Any | None = Field(
        default=None, sa_column=Column("answer", JSONB, nullable=True)
    )
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    cost_usd: float = 0.0
    attempts: int = 1
    # Why the last attempt failed: the error's type and message, never call content.
    error: str | None = Field(default=None, sa_column=Column("error", Text))
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
