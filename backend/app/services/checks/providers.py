"""Whether Connexity can ask a model check's provider at all."""

from app.core.config import settings
from app.services.checks.base import ModelProvider

_KEYS = {
    ModelProvider.TYPESAFE: "TYPESAFE_API_KEY",
    ModelProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    ModelProvider.OPENAI: "OPENAI_API_KEY",
}


def keys_present() -> tuple[str, ...]:
    """The provider key settings that are set now."""
    return tuple(name for name in _KEYS.values() if getattr(settings, name, None))


def missing_key(provider: ModelProvider) -> str | None:
    """The setting a provider needs that is empty, or None when it can be asked."""
    name = _KEYS[provider]
    return None if getattr(settings, name, None) else name
