"""Per-tenant LLM context resolution.

Translates a requested ``(model, provider)`` into an effective
``(litellm_model, api_key)`` pair using a company's configured credentials.

Backend features are provider-agnostic — when a feature pins a specific model,
this module rewrites it to a sensible equivalent on the user's available
provider so we never call OpenAI on behalf of a company that only configured
Anthropic (and vice versa).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from sqlmodel import Session

from app.core.db import engine
from app.crud.company import (
    company_has_any_llm_key,
    get_company,
    resolve_llm_api_key,
)
from app.models.company import Company, LLMProvider

logger = logging.getLogger(__name__)


# ── Ambient tenant context ─────────────────────────────────────────────
#
# Set once at the request / run boundary; every downstream ``call_llm`` reads
# this without having to thread the value through dozens of function signatures.
# A plain ``ContextVar`` is propagated automatically by ``asyncio.create_task``
# so this works for background eval runs too.

_current_tenant: ContextVar[LLMTenantContext | None] = ContextVar(
    "_current_tenant", default=None
)


def get_current_tenant() -> LLMTenantContext | None:
    return _current_tenant.get()


def set_current_tenant(tenant: LLMTenantContext | None) -> object:
    """Set the ambient tenant; returns the previous token (use ``reset_*``)."""
    return _current_tenant.set(tenant)


def reset_current_tenant(token: object) -> None:
    _current_tenant.reset(token)  # type: ignore[arg-type]


@contextmanager
def tenant_scope(tenant: LLMTenantContext | None) -> Iterator[None]:
    """``with tenant_scope(ctx): ...`` for synchronous + async code paths."""
    token = set_current_tenant(tenant)
    try:
        yield
    finally:
        reset_current_tenant(token)


def load_and_set_current_tenant(company_id: uuid.UUID) -> LLMTenantContext:
    """Convenience: load the tenant context and set it as ambient. Returns the
    context so the caller can keep using it directly if they prefer.
    """
    with Session(engine) as session:
        ctx = load_tenant_context(session=session, company_id=company_id)
    set_current_tenant(ctx)
    return ctx


@dataclass(frozen=True)
class LLMTenantContext:
    """Resolved per-tenant LLM credentials, computed once per request."""

    company_id: uuid.UUID
    openai_api_key: str | None
    anthropic_api_key: str | None
    preferred_provider: LLMProvider

    def has_provider(self, provider: LLMProvider) -> bool:
        if provider == LLMProvider.OPENAI:
            return self.openai_api_key is not None
        return self.anthropic_api_key is not None

    def api_key_for(self, provider: LLMProvider) -> str | None:
        if provider == LLMProvider.OPENAI:
            return self.openai_api_key
        return self.anthropic_api_key


class CompanyMissingLLMKeyError(RuntimeError):
    """Raised when an LLM call is attempted for a company without any keys."""


def load_tenant_context(*, session: Session, company_id: uuid.UUID) -> LLMTenantContext:
    """Load + decrypt a company's LLM credentials.

    Raises :class:`CompanyMissingLLMKeyError` when no keys are configured.
    """
    company = get_company(session=session, company_id=company_id)
    if company is None:
        msg = f"Company {company_id} not found"
        raise CompanyMissingLLMKeyError(msg)
    return tenant_context_from_company(company)


def tenant_context_from_company(company: Company) -> LLMTenantContext:
    if not company_has_any_llm_key(company=company):
        msg = (
            "This workspace has no LLM API key configured. Add an OpenAI or "
            "Anthropic key in Settings before running evaluations."
        )
        raise CompanyMissingLLMKeyError(msg)
    openai_key = resolve_llm_api_key(company=company, provider=LLMProvider.OPENAI)
    anthropic_key = resolve_llm_api_key(company=company, provider=LLMProvider.ANTHROPIC)
    # Pick a sane default if preferred_llm_provider got nulled out somehow.
    pref = company.preferred_llm_provider
    if pref is None:
        pref = LLMProvider.OPENAI if openai_key else LLMProvider.ANTHROPIC
    return LLMTenantContext(
        company_id=company.id,
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
        preferred_provider=pref,
    )


# ── Cross-provider model equivalences ────────────────────────────────
#
# When a feature pins a specific model the tenant doesn't have a key for,
# we rewrite to the closest equivalent on their available provider.
# Source-of-truth table is intentionally short — additions are cheap.

_OPENAI_FOR_ANTHROPIC: dict[str, str] = {
    # Sonnet / mid-tier
    "claude-sonnet-4-5": "gpt-4.1",
    "claude-3-5-sonnet": "gpt-4.1",
    # Haiku / small
    "claude-haiku-4-5": "gpt-4.1-mini",
    "claude-3-5-haiku": "gpt-4.1-mini",
    # Opus → gpt-4.1 (OpenAI has no opus-tier sibling)
    "claude-3-opus": "gpt-4.1",
    "claude-opus-4": "gpt-4.1",
}

_ANTHROPIC_FOR_OPENAI: dict[str, str] = {
    # GPT-4 tier
    "gpt-4.1": "claude-sonnet-4-5",
    "gpt-4o": "claude-sonnet-4-5",
    "gpt-4": "claude-sonnet-4-5",
    # Smaller
    "gpt-4.1-mini": "claude-haiku-4-5",
    "gpt-4o-mini": "claude-haiku-4-5",
    "gpt-4.1-nano": "claude-haiku-4-5",
    "gpt-3.5-turbo": "claude-haiku-4-5",
}

_DEFAULT_FALLBACK_OPENAI = "gpt-4.1-mini"
_DEFAULT_FALLBACK_ANTHROPIC = "claude-haiku-4-5"


def _strip_routing_prefix(model: str) -> tuple[str | None, str]:
    """Return ``(provider_prefix, bare_model)``.

    ``"anthropic/claude-sonnet-4-5"`` → ``("anthropic", "claude-sonnet-4-5")``
    ``"gpt-4.1"`` → ``(None, "gpt-4.1")``
    """
    if "/" in model:
        prefix, _, rest = model.partition("/")
        return prefix.lower(), rest
    return None, model


def _provider_from_model(model: str) -> LLMProvider | None:
    prefix, bare = _strip_routing_prefix(model)
    if prefix == "openai":
        return LLMProvider.OPENAI
    if prefix == "anthropic":
        return LLMProvider.ANTHROPIC
    lowered = bare.lower()
    if (
        lowered.startswith("gpt")
        or lowered.startswith("o1")
        or lowered.startswith("o3")
    ):
        return LLMProvider.OPENAI
    if lowered.startswith("claude"):
        return LLMProvider.ANTHROPIC
    return None


def _strip_anthropic_date_suffix(model: str) -> str:
    """``claude-3-5-sonnet-20241022`` → ``claude-3-5-sonnet``."""
    parts = model.split("-")
    if parts and parts[-1].isdigit() and len(parts[-1]) >= 6:
        return "-".join(parts[:-1])
    return model


def _map_anthropic_to_openai(model: str) -> str:
    bare = _strip_anthropic_date_suffix(model.lower())
    return _OPENAI_FOR_ANTHROPIC.get(bare, _DEFAULT_FALLBACK_OPENAI)


def _map_openai_to_anthropic(model: str) -> str:
    return _ANTHROPIC_FOR_OPENAI.get(model.lower(), _DEFAULT_FALLBACK_ANTHROPIC)


@dataclass(frozen=True)
class ResolvedLLMTarget:
    """The model + api_key actually sent to LiteLLM after tenant resolution."""

    litellm_model: str
    api_key: str
    provider: LLMProvider


def resolve_for_tenant(
    *,
    requested_model: str,
    requested_provider: str | None,
    tenant: LLMTenantContext,
) -> ResolvedLLMTarget:
    """Map a requested ``(model, provider)`` to what we can actually call.

    - If the request implies a provider the tenant has, use it.
    - Otherwise rewrite the model to the cross-provider equivalent and route
      via the tenant's available provider.
    - When the request is provider-neutral (no prefix, no hint), route via
      the tenant's preferred provider.
    """
    prefix, bare = _strip_routing_prefix(requested_model)
    implied = _provider_from_model(requested_model)
    if requested_provider:
        rp = requested_provider.strip().lower()
        if rp == "openai":
            implied = LLMProvider.OPENAI
        elif rp == "anthropic":
            implied = LLMProvider.ANTHROPIC

    # 1. If we can honor the request directly, do so.
    if implied is not None and tenant.has_provider(implied):
        api_key = tenant.api_key_for(implied)
        assert api_key is not None  # has_provider checked
        # Normalize to litellm "provider/model" form when the request didn't
        # already specify it.
        litellm_model = (
            requested_model if prefix is not None else f"{implied.value}/{bare}"
        )
        return ResolvedLLMTarget(
            litellm_model=litellm_model, api_key=api_key, provider=implied
        )

    # 2. Cross-provider rewrite: pick whichever provider the tenant has.
    target_provider = (
        LLMProvider.ANTHROPIC if implied == LLMProvider.OPENAI else LLMProvider.OPENAI
    )
    # If the implied-target swap doesn't match what we have either, fall back
    # to the tenant's actually-available provider.
    if not tenant.has_provider(target_provider):
        target_provider = (
            LLMProvider.OPENAI
            if tenant.openai_api_key is not None
            else LLMProvider.ANTHROPIC
        )
    api_key = tenant.api_key_for(target_provider)
    assert api_key is not None

    # Decide which model to swap in.
    if target_provider == LLMProvider.OPENAI:
        mapped_bare = _map_anthropic_to_openai(bare)
    else:
        mapped_bare = _map_openai_to_anthropic(bare)

    logger.debug(
        "Tenant %s rewriting model %s → %s/%s",
        tenant.company_id,
        requested_model,
        target_provider.value,
        mapped_bare,
    )
    return ResolvedLLMTarget(
        litellm_model=f"{target_provider.value}/{mapped_bare}",
        api_key=api_key,
        provider=target_provider,
    )
