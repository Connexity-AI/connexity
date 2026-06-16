from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    # Surfaces malformed/missing keys at first use rather than per-call
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def mask_key(key: str, visible: int = 4, dot_count: int = 4) -> str:
    """Render a short fixed-length mask: e.g. ``sk-p••••tuIA``.

    Earlier versions of this helper returned a string the same length as the
    input — that's fine for short Retell/Vapi-style keys but blows past the
    masked-key column for long Anthropic / OpenAI keys. A fixed-width mask
    keeps the display readable and the column small.
    """
    if len(key) <= visible * 2:
        return "•" * len(key)
    return key[:visible] + "•" * dot_count + key[-visible:]
