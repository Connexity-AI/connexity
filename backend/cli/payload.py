"""Shared helpers for loading JSON payloads from files or stdin.

The convention across the CLI: any command that accepts a complex request
body takes ``--from-file PATH`` (where ``-`` reads stdin). The data is parsed
as JSON and returned typed by ``load_dict_payload`` / ``load_list_payload``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _parse_json(raw: str) -> Any:
    if not raw.strip():
        raise click.ClickException("Empty payload — expected JSON.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON: {exc}") from exc


def load_dict_payload(path: str | None) -> dict[str, Any]:
    """Load a JSON object from ``path`` (or stdin if ``-``)."""
    if not path:
        raise click.ClickException("--from-file is required.")
    parsed = _parse_json(_read_text(path))
    if not isinstance(parsed, dict):
        raise click.ClickException("Expected a JSON object at the top level.")
    return parsed


def load_list_payload(path: str | None) -> list[Any]:
    """Load a JSON array from ``path`` (or stdin if ``-``)."""
    if not path:
        raise click.ClickException("--from-file is required.")
    parsed = _parse_json(_read_text(path))
    if not isinstance(parsed, list):
        raise click.ClickException("Expected a JSON array at the top level.")
    return parsed


def load_optional_dict(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    return load_dict_payload(path)
