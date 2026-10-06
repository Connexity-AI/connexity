import uuid
from datetime import UTC, datetime

from pydantic import model_validator
from sqlalchemy import text
from sqlmodel import Field, SQLModel

from app.models.enums import Platform


class EnvironmentBase(SQLModel):
    name: str = Field(max_length=255)
    platform: Platform = Field(...)


def _is_http_url(value: str) -> bool:
    lower = value.lower()
    return lower.startswith("http://") or lower.startswith("https://")


def validate_environment_platform_fields(
    *,
    platform: Platform,
    endpoint_url: str | None,
) -> None:
    if platform in {Platform.RETELL, Platform.VAPI, Platform.ELEVENLABS}:
        platform_value = platform.value
        if endpoint_url is not None:
            msg = f"endpoint_url must be null when platform is '{platform_value}'"
            raise ValueError(msg)
        return

    if platform == Platform.WEBHOOK:
        if endpoint_url is None or not endpoint_url.strip():
            msg = "endpoint_url is required when platform is 'webhook'"
            raise ValueError(msg)
        if not _is_http_url(endpoint_url.strip()):
            msg = "endpoint_url must start with http:// or https://"
            raise ValueError(msg)


class Environment(EnvironmentBase, table=True):
    __tablename__ = "environment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True)
    endpoint_url: str | None = Field(default=None, max_length=2048)
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


class EnvironmentCreate(EnvironmentBase):
    agent_id: uuid.UUID
    endpoint_url: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_platform_fields(self) -> "EnvironmentCreate":
        validate_environment_platform_fields(
            platform=self.platform,
            endpoint_url=self.endpoint_url,
        )
        return self


class EnvironmentUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    platform: Platform | None = None
    endpoint_url: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_required_update_fields(self) -> "EnvironmentUpdate":
        if "name" in self.model_fields_set and self.name is None:
            msg = "name cannot be null"
            raise ValueError(msg)
        if "platform" in self.model_fields_set and self.platform is None:
            msg = "platform cannot be null"
            raise ValueError(msg)
        return self


class EnvironmentPublic(EnvironmentBase):
    id: uuid.UUID
    agent_id: uuid.UUID
    integration_name: str | None
    endpoint_url: str | None
    created_at: datetime


class EnvironmentsPublic(SQLModel):
    data: list[EnvironmentPublic]
    count: int
