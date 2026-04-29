"""Strip legacy ``platform_config.mode`` from agent tool JSONB columns.

Revision ID: e8f9a0b1c2d3
Revises: d0e1f2a3b4c5
Create Date: 2026-04-29

"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "e8f9a0b1c2d3"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def _strip_mode_from_tools_list(tools: list[Any]) -> tuple[list[Any], bool]:
    changed = False
    out: list[Any] = []
    for item in tools:
        if not isinstance(item, dict):
            out.append(item)
            continue
        pc = item.get("platform_config")
        if isinstance(pc, dict) and "mode" in pc:
            changed = True
            new_item = dict(item)
            new_item["platform_config"] = {k: v for k, v in pc.items() if k != "mode"}
            out.append(new_item)
        else:
            out.append(item)
    return out, changed


def _normalize_tools_cell(raw: Any) -> tuple[list[Any] | None, bool]:
    if raw is None:
        return None, False
    tools = raw if isinstance(raw, list) else json.loads(raw)
    if not isinstance(tools, list):
        return None, False
    new_tools, changed = _strip_mode_from_tools_list(tools)
    return new_tools, changed


def upgrade() -> None:
    conn = op.get_bind()
    for table, column in (
        ("agent", "tools"),
        ("agent_version", "tools"),
        ("run", "agent_tools"),
    ):
        rows = conn.execute(
            sa.text(f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL")
        ).fetchall()
        for row_id, raw in rows:
            new_tools, changed = _normalize_tools_cell(raw)
            if not changed or new_tools is None:
                continue
            conn.execute(
                sa.text(
                    f"UPDATE {table} SET {column} = CAST(:val AS jsonb) WHERE id = :id"
                ),
                {"val": json.dumps(new_tools), "id": row_id},
            )


def downgrade() -> None:
    """Irreversible: original ``mode`` values are not preserved."""
