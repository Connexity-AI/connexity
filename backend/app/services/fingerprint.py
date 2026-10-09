"""Fingerprints of component content, and masking of what must not be stored.

A fingerprint is a hash of a component's content with the fields that change without
the content changing left out, so two versions with the same content share one.
Credentials are masked before hashing, so rotating a token is not a new version.
"""

import hashlib
import json
import re
from collections.abc import Collection
from typing import Any

MASK = "•••"

# Field names whose string value is a credential.
_SECRET_NAME = re.compile(
    r"api[_-]?key|access[_-]?key|private[_-]?key|token|secret|password|passwd"
    r"|passphrase|authorization|bearer|cookie|signature",
    re.IGNORECASE,
)


def mask_secrets(value: Any, *, _in_headers: bool = False) -> Any:
    """A copy of ``value`` with credentials replaced by a fixed mask.

    Masked: every value under a field whose name contains "header" (request headers,
    whether a mapping of name to value or a list of name and value pairs), the string
    value of any field named like a key, token, secret or password, and the ``value`` of
    a name and value pair whose ``name`` is such a name. Masking goes by names, never by
    what a value looks like.
    """
    if isinstance(value, list):
        return [mask_secrets(item, _in_headers=_in_headers) for item in value]
    if not isinstance(value, dict):
        return value
    masked: dict[str, Any] = {}
    pair_name = value.get("name")
    named_secret = isinstance(pair_name, str) and bool(_SECRET_NAME.search(pair_name))
    for key, item in value.items():
        name = str(key)
        inside = _in_headers or "header" in name.lower()
        if isinstance(item, str) and (
            _SECRET_NAME.search(name)
            or (inside and name != "name")
            or (named_secret and name == "value")
        ):
            masked[name] = MASK
        else:
            masked[name] = mask_secrets(item, _in_headers=inside)
    return masked


def without(content: dict[str, Any], fields: Collection[str]) -> dict[str, Any]:
    return {key: value for key, value in content.items() if key not in fields}


def fingerprint(content: Any) -> str:
    """SHA-256 of ``content`` in a canonical form: the same content, the same hash."""
    canonical = json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def combined_fingerprint(parts: dict[str, str]) -> str | None:
    """One fingerprint for several components, by kind. ``None`` when there are none."""
    return fingerprint(sorted(parts.items())) if parts else None
