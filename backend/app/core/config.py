import warnings
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    Field,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_VALUE: str = "changethis"


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    # Load .env file
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # ------- Required variables -------

    # Note: SITE_URL and database are actually REQUIRED variables but made optional
    # Note: to display dev friendly message in root route for deployments without env vars set

    # Frontend url
    SITE_URL: str | None = None  # truly required

    # DATABASE_URL | POSTGRES_* # truly required

    DATABASE_URL: PostgresDsn | None = None

    # Local / Docker fallback
    POSTGRES_SERVER: str | None = None
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None

    # ------- Optional variables -------

    # Secrets
    JWT_SECRET_KEY: str = DEFAULT_SECRET_VALUE
    # Fernet key for encrypting integration API keys — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = DEFAULT_SECRET_VALUE

    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    API_V1_STR: str = "/api/v1"
    AUTH_COOKIE: str = "auth_cookie"
    # Cookie expiration and JWT expiration match
    # 24 hours * 7 days = 168 hours
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24 * 7

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    PROJECT_NAME: str = "connexity"
    SENTRY_DSN: HttpUrl | None = None

    EMAIL_TEST_USER: EmailStr = "test@example.com"

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: EmailStr | None = None

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    # LLM — shared across generator, judge, simulator, etc.
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    LLM_DEFAULT_MODEL: str | None = None
    LLM_DEFAULT_PROVIDER: str | None = None
    LLM_RETRY_MAX_ATTEMPTS: int = 5
    LLM_RETRY_MIN_WAIT_SECONDS: float = 1.0
    LLM_RETRY_MAX_WAIT_SECONDS: float = 60.0

    # Judge-specific
    JUDGE_TEMPERATURE: float = 0.2
    JUDGE_MAX_TOKENS: int = 4096

    # Analysis-specific (CS-29)
    ANALYSIS_MODEL: str | None = None
    ANALYSIS_PROVIDER: str | None = None
    ANALYSIS_TEMPERATURE: float = 0.2
    ANALYSIS_MAX_TOKENS: int = 4096

    # Generator-specific
    GENERATOR_MAX_TOKENS: int = 16_000
    GENERATOR_TEMPERATURE: float = 0.9
    # Default weight for AI-generated custom metrics (not chosen by the LLM)
    GENERATOR_CUSTOM_METRIC_DEFAULT_WEIGHT: float = Field(default=0.15, ge=0.0)

    # ------- Computed properties -------

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        origins = [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]
        if self.SITE_URL:
            origins.append(self.SITE_URL)
        return origins

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn | None:
        # 1. DATABASE_URL (e.g. Neon)
        if self.DATABASE_URL:
            database_url = str(self.DATABASE_URL)
            # Force SQLAlchemy to use psycopg v3 (Neon provides postgresql:// by default)
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+psycopg://"
                )
            return PostgresDsn(database_url)

        # 2. POSTGRES_* (local development, Docker)
        if all(
            [
                self.POSTGRES_SERVER,
                self.POSTGRES_USER,
                self.POSTGRES_PASSWORD,
                self.POSTGRES_DB,
            ]
        ):
            return MultiHostUrl.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_SERVER,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )

        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    # ------- Validators -------

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    # Must run at end
    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        # required vars
        self._check_default_secret("JWT_SECRET_KEY", self.JWT_SECRET_KEY)
        self._check_default_secret("ENCRYPTION_KEY", self.ENCRYPTION_KEY)
        # conditional required vars
        if self.POSTGRES_PASSWORD:
            self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)

        return self

    # ------- Utilities -------

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == DEFAULT_SECRET_VALUE:
            message = (
                f"The value of {var_name} is {DEFAULT_SECRET_VALUE}, "
                "for security, please change it, at least for deployments."
            )
            # prevent exceptions for deployments without secrets set
            warnings.warn(message, stacklevel=1)


settings = Settings()
