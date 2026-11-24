"""Top-ups: the invoice a balance line was paid by, and auto top-up on the agency

Revision ID: 0054_top_ups
Revises: 0053_first_subscribed_at
Create Date: 2026-11-24 22:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision = '0054_top_ups'
down_revision = '0053_first_subscribed_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('balance_entry', sa.Column('stripe_invoice_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.create_unique_constraint('balance_entry_stripe_invoice_id_key', 'balance_entry', ['stripe_invoice_id'])
    op.add_column('agency', sa.Column('auto_top_up_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('agency', sa.Column('auto_top_up_amount_usd', sa.Integer(), server_default=sa.text('200'), nullable=False))
    op.add_column('agency', sa.Column('auto_top_up_invoice_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('agency', sa.Column('payment_failed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agency', sa.Column('payment_failed_amount_usd', sa.Integer(), nullable=True))
    op.add_column('agency', sa.Column('payment_failed_reason', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
    op.add_column('agency', sa.Column('payment_failed_card', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('agency', sa.Column('low_notified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agency', sa.Column('paused_notified_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for column in (
        'paused_notified_at', 'low_notified_at', 'payment_failed_card',
        'payment_failed_reason', 'payment_failed_amount_usd', 'payment_failed_at',
        'auto_top_up_invoice_id', 'auto_top_up_amount_usd',
        'auto_top_up_enabled',
    ):
        op.drop_column('agency', column)
    op.drop_constraint('balance_entry_stripe_invoice_id_key', 'balance_entry', type_='unique')
    op.drop_column('balance_entry', 'stripe_invoice_id')
