"""Override the session-scoped db fixture for model-only tests.

These tests do not require a database connection — they validate
Pydantic serialization and in-memory ORM model construction only.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def db():
    """No-op override: model tests don't need a database."""
    yield None
