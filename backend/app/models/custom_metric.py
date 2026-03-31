import re
import uuid
from datetime import UTC, datetime

from pydantic import field_validator
from sqlalchemy import Column, Text, UniqueConstraint, text
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.enums import MetricTier, ScoreType

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class CustomMetricBase(SQLModel):
    name: str = Field(max_length=255, description="Unique slug per owner (snake_case)")
    display_name: str = Field(max_length=255)
    description: str = Field(sa_column=Column(Text, nullable=False))
    tier: MetricTier = Field(
        sa_column=Column(
            SAEnum(
                MetricTier,
                name="metrictier",
                native_enum=True,
                values_callable=lambda m: [e.value for e in m],
            ),
            nullable=False,
        )
    )
    default_weight: float = Field(ge=0.0)
    score_type: ScoreType = Field(
        sa_column=Column(
            SAEnum(
                ScoreType,
                name="scoretype",
                native_enum=True,
                values_callable=lambda m: [e.value for e in m],
            ),
            nullable=False,
        )
    )
    rubric: str = Field(sa_column=Column(Text, nullable=False))
    include_in_defaults: bool = Field(default=False)

    @field_validator("name")
    @classmethod
    def validate_name_slug(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            msg = (
                "name must be snake_case: start with a letter, then lowercase "
                "letters, digits, underscores only"
            )
            raise ValueError(msg)
        return v


class CustomMetric(CustomMetricBase, table=True):
    __tablename__ = "custom_metric"
    __table_args__ = (
        UniqueConstraint("created_by", "name", name="uq_custom_metric_owner_name"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_by: uuid.UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={
            "server_default": text("now()"),
            "onupdate": lambda: datetime.now(UTC),
        },
    )


class CustomMetricCreate(CustomMetricBase):
    pass


class CustomMetricUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    tier: MetricTier | None = None
    default_weight: float | None = Field(default=None, ge=0.0)
    score_type: ScoreType | None = None
    rubric: str | None = None
    include_in_defaults: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name_slug(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _SLUG_RE.match(v):
            msg = (
                "name must be snake_case: start with a letter, then lowercase "
                "letters, digits, underscores only"
            )
            raise ValueError(msg)
        return v


class CustomMetricPublic(CustomMetricBase):
    id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CustomMetricsPublic(SQLModel):
    data: list[CustomMetricPublic] = Field(description="List of custom metrics")
    count: int = Field(description="Total number of custom metrics for the user")
