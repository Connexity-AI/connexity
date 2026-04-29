"""call unique per agent

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b5
Create Date: 2026-04-28 17:00:00.000000

Replaces the global UNIQUE on call.retell_call_id with a composite UNIQUE on
(retell_call_id, agent_id). One Retell call can now belong to multiple
Connexity agents independently — previously the first agent to sync claimed
the row and every other agent's upsert was silently dropped via ON CONFLICT.
"""

from alembic import op

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The original migration created the unique via `create_index(..., unique=True)`,
    # so it lives as a unique index named ix_call_retell_call_id, not a constraint.
    op.drop_index("ix_call_retell_call_id", table_name="call")
    op.create_index("ix_call_retell_call_id", "call", ["retell_call_id"], unique=False)
    op.create_unique_constraint(
        "uq_call_retell_call_agent", "call", ["retell_call_id", "agent_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_call_retell_call_agent", "call", type_="unique")
    op.drop_index("ix_call_retell_call_id", table_name="call")
    op.create_index("ix_call_retell_call_id", "call", ["retell_call_id"], unique=True)
