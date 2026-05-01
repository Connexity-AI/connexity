"""Reference resolution helpers — UUID-or-name lookup for common resources.

Shared across command modules so we don't duplicate the "is this a UUID?
otherwise list-and-fuzzy-match-by-name" pattern in every CRUD command.
"""

from __future__ import annotations

import uuid
from typing import Any

import click

from cli.api import ApiClient


def try_uuid(value: str) -> str | None:
    """Return the canonical UUID string if ``value`` parses as a UUID, else None."""
    try:
        return str(uuid.UUID(value.strip()))
    except (ValueError, AttributeError):
        return None


def _match_by_name(rows: list[Any], ref: str, *, resource: str) -> dict[str, Any]:
    ref_l = ref.strip().casefold()
    matches = [
        r
        for r in rows
        if isinstance(r, dict) and str(r.get("name", "")).casefold() == ref_l
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise click.ClickException(
            f"No {resource} found with name {ref!r}. Use a UUID or exact name."
        )
    names = ", ".join(str(m.get("name")) for m in matches[:5])
    raise click.ClickException(
        f"Multiple {resource} match {ref!r}: {names}. Use a UUID."
    )


def resolve_agent(client: ApiClient, ref: str) -> dict[str, Any]:
    """Return an agent dict by UUID, exact name, or registered endpoint URL."""
    uid = try_uuid(ref)
    if uid:
        return client.agents.get(uid)

    ref_stripped = ref.strip()
    rows = client.agents.list(params={"limit": 1000}).get("data") or []

    if ref_stripped.lower().startswith(("http://", "https://")):
        for a in rows:
            if not isinstance(a, dict):
                continue
            if str(a.get("endpoint_url", "")).rstrip("/") == ref_stripped.rstrip("/"):
                return a
        raise click.ClickException(
            f"No agent registered with endpoint_url matching {ref_stripped!r}. "
            "Create an agent in the UI/API first, or pass an agent UUID."
        )

    return _match_by_name(rows, ref, resource="agent")


def resolve_eval_config(client: ApiClient, ref: str) -> dict[str, Any]:
    """Return an eval config dict by UUID or exact name."""
    uid = try_uuid(ref)
    if uid:
        return client.eval_configs.get(uid)
    rows = client.eval_configs.list(params={"limit": 1000}).get("data") or []
    return _match_by_name(rows, ref, resource="eval config")


def resolve_test_case(client: ApiClient, ref: str) -> dict[str, Any]:
    """Return a test case dict by UUID or exact name (slow path lists 1000)."""
    uid = try_uuid(ref)
    if uid:
        return client.test_cases.get(uid)
    rows = client.test_cases.list(params={"limit": 1000}).get("data") or []
    return _match_by_name(rows, ref, resource="test case")
