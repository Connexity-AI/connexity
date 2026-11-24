"""An agency's prepaid balance, its pauses, and the included first scan

Revision ID: 0052_balance_and_pause
Revises: 0051_subscription
Create Date: 2026-11-24 17:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision = '0052_balance_and_pause'
down_revision = '0051_subscription'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('agent', sa.Column('scan_window_total', sa.Integer(), nullable=True))
    op.create_table(
        'balance_entry',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('agency_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.Enum('added', 'usage', name='balancekind', native_enum=False, length=32), nullable=False),
        sa.Column('amount_usd', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('note', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agency.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id', 'kind', 'period_start', name='uq_balance_entry_period'),
    )
    op.create_index(op.f('ix_balance_entry_agency_id'), 'balance_entry', ['agency_id'], unique=False)
    op.create_table(
        'billing_pause',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('agency_id', sa.Uuid(), nullable=False),
        sa.Column('reason', sa.Enum('first_scan', 'needs_subscription', 'active', 'low', 'out', 'unpaid', name='agencystate', native_enum=False, length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agency.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_billing_pause_agency_id'), 'billing_pause', ['agency_id'], unique=False)
    op.create_table(
        'included_scan',
        sa.Column('key_fingerprint', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('agency_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agency.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('key_fingerprint'),
    )


def downgrade() -> None:
    op.drop_table('included_scan')
    op.drop_index(op.f('ix_billing_pause_agency_id'), table_name='billing_pause')
    op.drop_table('billing_pause')
    op.drop_index(op.f('ix_balance_entry_agency_id'), table_name='balance_entry')
    op.drop_table('balance_entry')
    op.drop_column('agent', 'scan_window_total')
