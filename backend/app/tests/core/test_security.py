"""The app hashes passwords at bcrypt's full cost; only the test run is cheap
(`plans/2026-11-26-fast-test-hashing.md`)."""

from passlib.context import CryptContext

from app.core import security
from app.tests.conftest import TEST_BCRYPT_ROUNDS


def _rounds(hashed: str) -> int:
    # "$2b$12$<salt and hash>": the cost is the third field.
    return int(hashed.split("$")[2])


def test_the_app_hashes_at_full_cost(production_pwd_context: CryptContext) -> None:
    hashed = production_pwd_context.hash("an invented password")
    assert hashed.startswith("$2b$")
    assert _rounds(hashed) >= 12
    assert production_pwd_context.verify("an invented password", hashed)


def test_tests_hash_cheaply_and_the_app_still_reads_those_hashes(
    production_pwd_context: CryptContext,
) -> None:
    hashed = security.get_password_hash("an invented password")
    assert _rounds(hashed) == TEST_BCRYPT_ROUNDS
    assert security.verify_password("an invented password", hashed)
    assert production_pwd_context.verify("an invented password", hashed)
