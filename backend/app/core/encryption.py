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


def mask_key(key: str, visible: int = 4) -> str:
    if len(key) <= visible * 2:
        return "•" * len(key)
    return key[:visible] + "•" * (len(key) - visible * 2) + key[-visible:]
