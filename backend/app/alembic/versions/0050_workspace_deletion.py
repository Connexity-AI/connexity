"""Deleting a workspace's data: the agency's record, and the rows that stay

Revision ID: 0050_workspace_deletion
Revises: 0049_agency_invite
Create Date: 2026-11-24 09:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision = '0050_workspace_deletion'
down_revision = '0049_agency_invite'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('company', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agent', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        'workspace_deletion',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('agency_id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('workspace_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('deleted_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('deleted_by_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('state', sa.Enum('deleting', 'done', 'failed', name='deletionstate', native_enum=False, length=32), nullable=False),
        sa.Column('calls', sa.Integer(), nullable=False),
        sa.Column('agents', sa.Integer(), nullable=False),
        sa.Column('issues', sa.Integer(), nullable=False),
        sa.Column('error', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agency.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['company.id']),
        sa.ForeignKeyConstraint(['deleted_by_user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id'),
    )
    op.create_index(op.f('ix_workspace_deletion_agency_id'), 'workspace_deletion', ['agency_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_workspace_deletion_agency_id'), table_name='workspace_deletion')
    op.drop_table('workspace_deletion')
    op.drop_column('agent', 'deleted_at')
    op.drop_column('company', 'deleted_at')
