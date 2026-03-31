"""add cost breakdown and per-turn latency to scenario_result

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-31 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenario_result",
        sa.Column("agent_latency_per_turn_ms", JSONB, nullable=True),
    )
    op.add_column(
        "scenario_result",
        sa.Column("agent_cost_usd", sa.Float, nullable=True),
    )
    op.add_column(
        "scenario_result",
        sa.Column("platform_cost_usd", sa.Float, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scenario_result", "platform_cost_usd")
    op.drop_column("scenario_result", "agent_cost_usd")
    op.drop_column("scenario_result", "agent_latency_per_turn_ms")
