"""ingest token: a credential that can only send traces

Revision ID: 0003_ingest_token
Revises: 0002_call_trace
Create Date: 2026-10-08

Only a hash of each token is stored.
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0003_ingest_token'
down_revision = '0002_call_trace'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('ingest_token',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('prefix', sqlmodel.sql.sqltypes.AutoString(length=12), nullable=False),
    sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_used_at', sa.DateTime(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ingest_token_company_id'), 'ingest_token', ['company_id'], unique=False)
    op.create_index(op.f('ix_ingest_token_token_hash'), 'ingest_token', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_ingest_token_token_hash'), table_name='ingest_token')
    op.drop_index(op.f('ix_ingest_token_company_id'), table_name='ingest_token')
    op.drop_table('ingest_token')
