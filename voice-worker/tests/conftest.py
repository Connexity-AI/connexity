"""Shared pytest fixtures and env defaults for voice-worker tests."""

from __future__ import annotations

import os

# voice_runner.main imports app.core.db at module load; provide dummy DB config
# for unit tests that do not open a real connection.
os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "password")
os.environ.setdefault("POSTGRES_DB", "app")
