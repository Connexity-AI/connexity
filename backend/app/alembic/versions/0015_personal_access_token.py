"""personal access tokens: Claude Code connects without a sign-in

Revision ID: 0015_personal_access_token
Revises: 0014_agent_first_scan
Create Date: 2026-11-13 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0015_personal_access_token'
down_revision = '0014_agent_first_scan'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'personal_access_token',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('prefix', sqlmodel.sql.sqltypes.AutoString(length=12), nullable=False),
        sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_personal_access_token_token_hash'), 'personal_access_token', ['token_hash'], unique=True)
    op.create_index(op.f('ix_personal_access_token_user_id'), 'personal_access_token', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_personal_access_token_user_id'), table_name='personal_access_token')
    op.drop_index(op.f('ix_personal_access_token_token_hash'), table_name='personal_access_token')
    op.drop_table('personal_access_token')
