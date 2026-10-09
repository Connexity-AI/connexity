"""The catalogue of component versions Connexity has seen serving an agent's calls.

A component is one of the things that serve a call: the agent's settings, its prompt,
its model, a skill (a backend workflow). Each version seen is kept once, with its
content, so that "which version was this call on" has an exact answer and a later
slice can say what changed between two versions.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import JsonValue
from sqlalchemy import Column, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

# The kinds that make up a call's combined fingerprint. Every call has them; a skill is
# left out because a call only knows the versions of the workflows it used.
STATE_KINDS = ("agent", "prompt", "flow", "model")


class ComponentVersion(SQLModel, table=True):
    __tablename__ = "component_version"
    __table_args__ = (
        UniqueConstraint(
            "agent_id", "kind", "ref", "version", name="uq_component_version_identity"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("agent.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    kind: str = Field(max_length=64)
    name: str = Field(max_length=255)
    ref: str = Field(max_length=255, description="The provider's id for the thing")
    version: str = Field(
        default="", max_length=255, description="Empty when the thing has no versions"
    )
    fingerprint: str = Field(max_length=64, index=True)
    content: Any = Field(
        default=None, sa_column=Column("content", JSONB(none_as_null=True))
    )
    # The other components this version points to: an agent version to its prompt
    # version and model. A list of {kind, ref, version}.
    links: list[dict[str, str]] | None = Field(
        default=None, sa_column=Column("links", JSONB(none_as_null=True))
    )
    first_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class ComponentVersionSummary(SQLModel):
    id: uuid.UUID
    kind: str
    name: str
    ref: str
    version: str
    fingerprint: str
    first_seen_at: datetime


class ComponentVersionPublic(ComponentVersionSummary):
    content: JsonValue = None


class ServedBy(SQLModel):
    """One thing that served a call, with the version that was live."""

    kind: str
    name: str
    ref: str | None = None
    version: str | None = None
    fingerprint: str | None = None
    # The catalogue entry holding this version's content, when Connexity has it.
    component_version_id: uuid.UUID | None = None


class VersionResolveResult(SQLModel):
    """What resolving an agent's stored calls did."""

    calls_resolved: int = Field(description="Calls that now list what served them")
    calls_unresolved: int = Field(description="Calls whose version could not be read")
    versions_read: int = Field(description="Agent versions read from the provider")
    skills_recorded: int = Field(description="Workflow versions newly recorded")
    problems: list[str] = []
