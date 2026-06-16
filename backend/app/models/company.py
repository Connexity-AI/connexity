import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, Text, text
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class LLMProvider(str, enum.Enum):
    """LLM providers a company can use for evaluations + test case generation.

    Backend features are provider-agnostic — they use whichever provider the
    company has a key for, with model auto-rerouting at the LLM service layer.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Company(SQLModel, table=True):
    __tablename__ = "company"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )

    # ── Per-tenant LLM credentials ─────────────────────────────────────
    # Encrypted (Fernet) provider keys + masked previews for the UI. At least
    # one must be set before LLM-backed features (evals, test case generation,
    # prompt editor, analysis) can run.
    openai_api_key_encrypted: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    openai_api_key_masked: str | None = Field(default=None, max_length=128)
    anthropic_api_key_encrypted: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    anthropic_api_key_masked: str | None = Field(default=None, max_length=128)

    # Default provider when a feature doesn't pin a specific one. UI sets this
    # from the provider the user chose during onboarding.
    preferred_llm_provider: LLMProvider | None = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                LLMProvider,
                name="llmprovider",
                native_enum=True,
                values_callable=lambda m: [e.value for e in m],
            ),
            nullable=True,
        ),
    )


class CompanyLLMCredentialsPublic(SQLModel):
    """Masked view of a company's LLM credentials for the settings page."""

    openai_api_key_masked: str | None = None
    anthropic_api_key_masked: str | None = None
    preferred_llm_provider: LLMProvider | None = None
    has_any_llm_key: bool = Field(
        description="True when at least one provider key is configured"
    )


class CompanyLLMCredentialsUpdate(SQLModel):
    """Payload to set or rotate a company's LLM credentials.

    Either ``openai_api_key`` or ``anthropic_api_key`` (or both) must be
    provided on initial onboarding. When updating, an empty value clears
    that provider's key.
    """

    openai_api_key: str | None = Field(
        default=None,
        description=(
            "OpenAI API key. Set to empty string to clear; omit to leave unchanged."
        ),
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description=(
            "Anthropic API key. Set to empty string to clear; omit to leave unchanged."
        ),
    )
    preferred_llm_provider: LLMProvider | None = Field(
        default=None,
        description="Default provider when a feature doesn't pin one. Required at onboarding.",
    )
