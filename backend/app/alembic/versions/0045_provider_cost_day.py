"""What a model provider billed for a day, beside what Connexity recorded

Revision ID: 0045_provider_cost_day
Revises: 0044_usage_record
Create Date: 2026-11-23 12:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision = '0045_provider_cost_day'
down_revision = '0044_usage_record'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'provider_cost_day',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('model', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('billed_usd', sa.Float(), nullable=False),
        sa.Column('billed_input_tokens', sa.BigInteger(), nullable=False),
        sa.Column('billed_output_tokens', sa.BigInteger(), nullable=False),
        sa.Column('billed_cache_read_tokens', sa.BigInteger(), nullable=False),
        sa.Column('billed_cache_write_tokens', sa.BigInteger(), nullable=False),
        sa.Column('recorded_usd', sa.Float(), nullable=False),
        sa.Column('recorded_input_tokens', sa.BigInteger(), nullable=False),
        sa.Column('recorded_output_tokens', sa.BigInteger(), nullable=False),
        sa.Column('recorded_cache_read_tokens', sa.BigInteger(), nullable=False),
        sa.Column('recorded_cache_write_tokens', sa.BigInteger(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('day', 'provider', 'model', name='uq_provider_cost_day_day_provider_model'),
    )


def downgrade() -> None:
    op.drop_table('provider_cost_day')
