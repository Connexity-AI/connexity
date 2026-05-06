"""environment eval gate: eval_gate_eval_config_id

Revision ID: m0n1o2p3q4r5
Revises: l9m0n1o2p3q4
Create Date: 2026-05-05 00:05:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "m0n1o2p3q4r5"
down_revision = "l9m0n1o2p3q4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "environment",
        sa.Column("eval_gate_eval_config_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_environment_eval_gate_eval_config_id_eval_config",
        "environment",
        "eval_config",
        ["eval_gate_eval_config_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_environment_eval_gate_eval_config_id"),
        "environment",
        ["eval_gate_eval_config_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_environment_eval_gate_eval_config_id"),
        table_name="environment",
    )
    op.drop_constraint(
        "fk_environment_eval_gate_eval_config_id_eval_config",
        "environment",
        type_="foreignkey",
    )
    op.drop_column("environment", "eval_gate_eval_config_id")
