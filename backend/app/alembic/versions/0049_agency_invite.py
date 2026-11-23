"""Invites to join an agency

Revision ID: 0049_agency_invite
Revises: 0048_agency
Create Date: 2026-11-23 22:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0049_agency_invite'
down_revision = '0048_agency'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'agency_invite',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('agency_id', sa.Uuid(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'member', name='agencyrole', native_enum=False, length=32), nullable=False),
        sa.Column('all_workspaces', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('workspace_ids', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('can_approve', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('invited_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agency.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by_user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agency_invite_agency_id'), 'agency_invite', ['agency_id'], unique=False)
    op.create_index(op.f('ix_agency_invite_email'), 'agency_invite', ['email'], unique=False)
    op.create_index(op.f('ix_agency_invite_token_hash'), 'agency_invite', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_agency_invite_token_hash'), table_name='agency_invite')
    op.drop_index(op.f('ix_agency_invite_email'), table_name='agency_invite')
    op.drop_index(op.f('ix_agency_invite_agency_id'), table_name='agency_invite')
    op.drop_table('agency_invite')
