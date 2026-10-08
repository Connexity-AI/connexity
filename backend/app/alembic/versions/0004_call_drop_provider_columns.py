"""call: drop the columns that held provider-shaped data

Revision ID: 0004_call_drop_provider_columns
Revises: 0003_ingest_token
Create Date: 2026-10-08

A call's conversation now lives in its trace (call_event). The provider's original
payload stays in call.raw. Downgrading restores the columns empty.
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0004_call_drop_provider_columns'
down_revision = '0003_ingest_token'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('call', 'transcript')
    op.drop_column('call', 'status')
    op.drop_column('call', 'duration_seconds')


def downgrade() -> None:
    op.add_column('call', sa.Column('duration_seconds', sa.Integer(), nullable=True))
    op.add_column('call', sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('call', sa.Column('transcript', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
