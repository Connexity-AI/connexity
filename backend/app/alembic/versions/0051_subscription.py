"""The agency's subscription, and Stripe's handled messages

Revision ID: 0051_subscription
Revises: 0050_workspace_deletion
Create Date: 2026-11-24 14:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision = '0051_subscription'
down_revision = '0050_workspace_deletion'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('agency', sa.Column('stripe_customer_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('agency', sa.Column('stripe_subscription_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('agency', sa.Column('subscription_state', sa.Enum('none', 'active', 'past_due', 'unpaid', 'ended', name='subscriptionstate', native_enum=False, length=32), server_default=sa.text("'none'"), nullable=False))
    op.add_column('agency', sa.Column('subscription_period_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agency', sa.Column('subscription_period_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agency', sa.Column('subscription_ends_at_period_end', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_unique_constraint('agency_stripe_customer_id_key', 'agency', ['stripe_customer_id'])
    op.create_table(
        'stripe_event',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('stripe_event')
    op.drop_constraint('agency_stripe_customer_id_key', 'agency', type_='unique')
    op.drop_column('agency', 'subscription_ends_at_period_end')
    op.drop_column('agency', 'subscription_period_end')
    op.drop_column('agency', 'subscription_period_start')
    op.drop_column('agency', 'subscription_state')
    op.drop_column('agency', 'stripe_subscription_id')
    op.drop_column('agency', 'stripe_customer_id')
