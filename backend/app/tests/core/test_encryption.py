from collections.abc import Generator

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.core import encryption
from app.core.encryption import decrypt, encrypt, mask_key


@pytest.fixture(autouse=True)
def _reset_fernet_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    yield
    encryption._fernet.cache_clear()


def test_encrypt_decrypt_roundtrip() -> None:
    plaintext = "sk_test_abc123XYZ"
    cipher = encrypt(plaintext)
    assert cipher != plaintext
    assert decrypt(cipher) == plaintext


def test_decrypt_fails_under_different_key(monkeypatch: pytest.MonkeyPatch) -> None:
    cipher = encrypt("secret-token")
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    with pytest.raises(InvalidToken):
        decrypt(cipher)


def test_mask_key_long_value() -> None:
    masked = mask_key("abcdefghijklmnopqrstuvwxyz")
    assert masked.startswith("abcd")
    assert masked.endswith("wxyz")
    assert "•" in masked
    assert len(masked) == len("abcdefghijklmnopqrstuvwxyz")


def test_mask_key_short_value_fully_masked() -> None:
    assert mask_key("abc") == "•••"
    assert mask_key("abcdefgh") == "•" * 8


def test_invalid_encryption_key_raises_on_first_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(encryption.settings, "ENCRYPTION_KEY", "not-a-fernet-key")
    encryption._fernet.cache_clear()
    with pytest.raises(ValueError):
        encrypt("anything")
