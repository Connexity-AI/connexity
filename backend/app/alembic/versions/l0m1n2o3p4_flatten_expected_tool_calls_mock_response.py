"""Flatten legacy expected_tool_calls mock_responses to mock_response rows.

Revision ID: l0m1n2o3p4
Revises: k8l9m0n1o2p3
Create Date: 2026-05-05

Each legacy ``mock_responses`` entry becomes its own expected_tool_calls element
with ``mock_response`` (from ``response``) and merged ``expected_params``.
"""

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "l0m1n2o3p4"
down_revision = "k8l9m0n1o2p3"
branch_labels = None
depends_on = None


def _drop_mock_responses(item: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in item.items() if k != "mock_responses"}


def _flatten_expected_tool_calls(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, list):
        return value

    flat: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            flat.append(item)
            continue

        if "mock_response" in item:
            flat.append(_drop_mock_responses(item))
            continue

        legacy = item.get("mock_responses")
        if not legacy:
            flat.append(_drop_mock_responses(item))
            continue

        if not isinstance(legacy, list):
            flat.append(_drop_mock_responses(item))
            continue

        base = _drop_mock_responses(item)
        for mr in legacy:
            if not isinstance(mr, dict):
                continue
            routed = mr.get("expected_params")
            merged_expected = (
                base.get("expected_params") if routed is None else routed
            )
            flat.append(
                {
                    **base,
                    "expected_params": merged_expected,
                    "mock_response": mr.get("response"),
                }
            )

    return flat


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, expected_tool_calls FROM test_case "
            "WHERE expected_tool_calls IS NOT NULL"
        )
    ).fetchall()
    for row_id, raw in rows:
        if raw is None:
            continue
        calls = raw if isinstance(raw, list) else json.loads(raw)  # type: ignore[arg-type]
        if not isinstance(calls, list):
            continue
        flattened = _flatten_expected_tool_calls(calls)
        if flattened == calls:
            continue
        conn.execute(
            sa.text(
                "UPDATE test_case SET expected_tool_calls = CAST(:val AS jsonb) "
                "WHERE id = :id"
            ),
            {"val": json.dumps(flattened), "id": row_id},
        )


def downgrade() -> None:
    """Irreversible: mock_responses list structure cannot be recovered from rows."""
