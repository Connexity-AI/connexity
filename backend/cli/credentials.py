"""Persistent credential storage for the CLI.

Credentials live at ``$XDG_CONFIG_HOME/connexity-cli/credentials.json``
(falling back to ``~/.config/connexity-cli/credentials.json``) with mode
``0600``. Storage is opt-in — ``connexity-cli login`` writes the file only
when ``--save`` is passed.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any, TypedDict


class StoredCredentials(TypedDict, total=False):
    api_url: str
    token: str
    expires: int  # Unix timestamp (seconds)
    email: str


def _config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    return (
        Path(base) / "connexity-cli"
        if base
        else Path.home() / ".config" / "connexity-cli"
    )


def credentials_path() -> Path:
    return _config_dir() / "credentials.json"


def load() -> StoredCredentials:
    """Read the credentials file, or ``{}`` if it does not exist or is malformed."""
    path = credentials_path()
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        parsed: Any = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    out: StoredCredentials = {}
    for key in ("api_url", "token", "email"):
        val = parsed.get(key)
        if isinstance(val, str):
            out[key] = val  # type: ignore[literal-required]
    expires = parsed.get("expires")
    if isinstance(expires, int):
        out["expires"] = expires
    return out


def save(payload: StoredCredentials) -> Path:
    """Write the credentials file with mode 0600. Returns the path written."""
    directory = _config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, stat.S_IRWXU)  # 0700
    except OSError:
        # Best effort — Windows / restricted FS. Continue.
        pass
    path = credentials_path()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass
    return path


def clear() -> bool:
    """Remove the credentials file. Returns True if a file was deleted."""
    path = credentials_path()
    if not path.exists():
        return False
    path.unlink()
    return True
