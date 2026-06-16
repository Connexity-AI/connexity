"""Company-scoped settings endpoints — currently LLM credential management."""

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app import crud
from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.models.company import (
    CompanyLLMCredentialsPublic,
    CompanyLLMCredentialsUpdate,
    LLMProvider,
)

router = APIRouter(
    prefix="/company",
    tags=["company"],
    dependencies=[Depends(get_current_user)],
)


async def _validate_openai_key(key: str) -> bool:
    """Cheap sanity check — list models with the key."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            return r.status_code == 200
    except Exception:
        return False


async def _validate_anthropic_key(key: str) -> bool:
    """Cheap sanity check — call the messages endpoint with a tiny payload."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            # 200 → key works. 400 with a model-not-found-style error also
            # means the key authenticated successfully — we just chose a
            # model the account can't see. 401/403 are real failures.
            if r.status_code == 200:
                return True
            return r.status_code not in {401, 403}
    except Exception:
        return False


@router.get("/llm-credentials", response_model=CompanyLLMCredentialsPublic)
def get_llm_credentials(
    session: SessionDep, company_id: CurrentCompany
) -> CompanyLLMCredentialsPublic:
    company = crud.get_company(session=session, company_id=company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return crud.company_llm_credentials_public(company=company)


@router.put("/llm-credentials", response_model=CompanyLLMCredentialsPublic)
async def update_llm_credentials(
    session: SessionDep,
    company_id: CurrentCompany,
    payload: CompanyLLMCredentialsUpdate,
) -> CompanyLLMCredentialsPublic:
    """Set or rotate the company's LLM credentials.

    Validates the key against the provider's API before persisting so we don't
    save a typoed key the user will hit at evaluation time.
    """
    company = crud.get_company(session=session, company_id=company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    if (
        payload.openai_api_key is not None
        and payload.openai_api_key.strip()
        and not await _validate_openai_key(payload.openai_api_key.strip())
    ):
        raise HTTPException(
            status_code=400,
            detail="OpenAI key could not be validated — check the key and try again.",
        )
    if (
        payload.anthropic_api_key is not None
        and payload.anthropic_api_key.strip()
        and not await _validate_anthropic_key(payload.anthropic_api_key.strip())
    ):
        raise HTTPException(
            status_code=400,
            detail="Anthropic key could not be validated — check the key and try again.",
        )

    # Require at least one provider key after the update; require preferred
    # provider when any key is present.
    after_openai = payload.openai_api_key
    after_anthropic = payload.anthropic_api_key

    will_have_openai = (
        bool(after_openai and after_openai.strip())
        if after_openai is not None
        else bool(company.openai_api_key_encrypted)
    )
    will_have_anthropic = (
        bool(after_anthropic and after_anthropic.strip())
        if after_anthropic is not None
        else bool(company.anthropic_api_key_encrypted)
    )
    if not (will_have_openai or will_have_anthropic):
        raise HTTPException(
            status_code=422,
            detail="At least one of OpenAI or Anthropic API key must be set.",
        )

    pref = payload.preferred_llm_provider or company.preferred_llm_provider
    if pref is None:
        # Derive a sensible default from whichever key the user provided.
        pref = LLMProvider.OPENAI if will_have_openai else LLMProvider.ANTHROPIC
    if pref == LLMProvider.OPENAI and not will_have_openai:
        pref = LLMProvider.ANTHROPIC
    elif pref == LLMProvider.ANTHROPIC and not will_have_anthropic:
        pref = LLMProvider.OPENAI

    payload_with_pref = payload.model_copy(update={"preferred_llm_provider": pref})

    updated = crud.update_llm_credentials(
        session=session, company=company, payload=payload_with_pref
    )
    return crud.company_llm_credentials_public(company=updated)
