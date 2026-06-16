"""CRUD for the ``company`` table — mainly LLM credential management."""

import uuid

from sqlmodel import Session

from app.core.encryption import decrypt, encrypt, mask_key
from app.models.company import (
    Company,
    CompanyLLMCredentialsPublic,
    CompanyLLMCredentialsUpdate,
    LLMProvider,
)


def get_company(*, session: Session, company_id: uuid.UUID) -> Company | None:
    return session.get(Company, company_id)


def company_llm_credentials_public(*, company: Company) -> CompanyLLMCredentialsPublic:
    has_any = bool(company.openai_api_key_encrypted) or bool(
        company.anthropic_api_key_encrypted
    )
    return CompanyLLMCredentialsPublic(
        openai_api_key_masked=company.openai_api_key_masked,
        anthropic_api_key_masked=company.anthropic_api_key_masked,
        preferred_llm_provider=company.preferred_llm_provider,
        has_any_llm_key=has_any,
    )


def update_llm_credentials(
    *,
    session: Session,
    company: Company,
    payload: CompanyLLMCredentialsUpdate,
) -> Company:
    """Encrypt + persist provider keys. ``""`` clears, ``None`` leaves alone."""
    if payload.openai_api_key is not None:
        if payload.openai_api_key.strip() == "":
            company.openai_api_key_encrypted = None
            company.openai_api_key_masked = None
        else:
            key = payload.openai_api_key.strip()
            company.openai_api_key_encrypted = encrypt(key)
            company.openai_api_key_masked = mask_key(key)

    if payload.anthropic_api_key is not None:
        if payload.anthropic_api_key.strip() == "":
            company.anthropic_api_key_encrypted = None
            company.anthropic_api_key_masked = None
        else:
            key = payload.anthropic_api_key.strip()
            company.anthropic_api_key_encrypted = encrypt(key)
            company.anthropic_api_key_masked = mask_key(key)

    if payload.preferred_llm_provider is not None:
        company.preferred_llm_provider = payload.preferred_llm_provider

    # Keep preferred_llm_provider consistent — if the user clears the chosen
    # provider's key but the other one is set, point preferred at that.
    if (
        company.preferred_llm_provider == LLMProvider.OPENAI
        and company.openai_api_key_encrypted is None
        and company.anthropic_api_key_encrypted is not None
    ):
        company.preferred_llm_provider = LLMProvider.ANTHROPIC
    elif (
        company.preferred_llm_provider == LLMProvider.ANTHROPIC
        and company.anthropic_api_key_encrypted is None
        and company.openai_api_key_encrypted is not None
    ):
        company.preferred_llm_provider = LLMProvider.OPENAI
    if (
        company.openai_api_key_encrypted is None
        and company.anthropic_api_key_encrypted is None
    ):
        company.preferred_llm_provider = None

    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def resolve_llm_api_key(*, company: Company, provider: LLMProvider) -> str | None:
    """Return the decrypted API key for ``provider``, or None if missing."""
    if provider == LLMProvider.OPENAI:
        if not company.openai_api_key_encrypted:
            return None
        return decrypt(company.openai_api_key_encrypted)
    if provider == LLMProvider.ANTHROPIC:
        if not company.anthropic_api_key_encrypted:
            return None
        return decrypt(company.anthropic_api_key_encrypted)
    return None


def company_has_any_llm_key(*, company: Company) -> bool:
    return bool(company.openai_api_key_encrypted or company.anthropic_api_key_encrypted)
