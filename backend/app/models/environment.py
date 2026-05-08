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
    integration_id: uuid.UUID | None,
    platform_agent_id: str | None,
    endpoint_url: str | None,
) -> None:
    if platform in {Platform.RETELL, Platform.VAPI}:
        platform_value = platform.value
        if integration_id is None:
            msg = f"integration_id is required when platform is '{platform_value}'"
            raise ValueError(msg)
        if platform_agent_id is None or not platform_agent_id.strip():
            msg = f"platform_agent_id is required when platform is '{platform_value}'"
            raise ValueError(msg)
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
        if integration_id is not None:
            msg = "integration_id must be null when platform is 'webhook'"
            raise ValueError(msg)
        if platform_agent_id is not None:
            msg = "platform_agent_id must be null when platform is 'webhook'"
            raise ValueError(msg)


class Environment(EnvironmentBase, table=True):
    __tablename__ = "environment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True)
    integration_id: uuid.UUID | None = Field(
        default=None, foreign_key="integration.id", index=True
    )
    platform_agent_id: str | None = Field(default=None, max_length=255, index=True)
    platform_agent_name: str | None = Field(default=None, max_length=255)
    endpoint_url: str | None = Field(default=None, max_length=2048)
    current_version_number: int | None = Field(default=None)
    current_version_name: str | None = Field(default=None, max_length=255)
    current_deployed_at: datetime | None = Field(default=None)
    eval_gate_eval_config_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="eval_config.id",
        index=True,
        description=(
            "When set, deploys to this environment are gated on a passing run "
            "of this eval config for the requested agent version."
        ),
    )
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
    integration_id: uuid.UUID | None = None
    platform_agent_id: str | None = None
    platform_agent_name: str | None = None
    endpoint_url: str | None = Field(default=None, max_length=2048)
    eval_gate_eval_config_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Optional: gate deploys on a passing run of this eval config for "
            "the requested agent version."
        ),
    )

    @model_validator(mode="after")
    def validate_platform_fields(self) -> "EnvironmentCreate":
        validate_environment_platform_fields(
            platform=self.platform,
            integration_id=self.integration_id,
            platform_agent_id=self.platform_agent_id,
            endpoint_url=self.endpoint_url,
        )
        return self


class EnvironmentUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    platform: Platform | None = None
    integration_id: uuid.UUID | None = None
    platform_agent_id: str | None = None
    platform_agent_name: str | None = None
    endpoint_url: str | None = Field(default=None, max_length=2048)
    eval_gate_eval_config_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Optional: gate deploys on a passing run of this eval config for "
            "the requested agent version."
        ),
    )

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
    integration_id: uuid.UUID | None
    integration_name: str | None
    platform_agent_id: str | None
    platform_agent_name: str | None
    endpoint_url: str | None
    current_version_number: int | None
    current_version_name: str | None
    current_deployed_at: datetime | None
    eval_gate_eval_config_id: uuid.UUID | None
    created_at: datetime


class EnvironmentsPublic(SQLModel):
    data: list[EnvironmentPublic]
    count: int
