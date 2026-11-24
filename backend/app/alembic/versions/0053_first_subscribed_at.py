"""When an agency's first subscription began

Revision ID: 0053_first_subscribed_at
Revises: 0052_balance_and_pause
Create Date: 2026-11-24 20:00:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '0053_first_subscribed_at'
down_revision = '0052_balance_and_pause'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('agency', sa.Column('first_subscribed_at', sa.DateTime(timezone=True), nullable=True))
    # An agency that already has a subscription: its current period is the earliest
    # start that is known.
    op.execute(
        "UPDATE agency SET first_subscribed_at = subscription_period_start "
        "WHERE subscription_period_start IS NOT NULL "
        "AND subscription_state IN ('active', 'past_due', 'unpaid', 'ended')"
    )


def downgrade() -> None:
    op.drop_column('agency', 'first_subscribed_at')
