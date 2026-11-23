"""Password reset requests and the session version that ends web sessions

Revision ID: 0046_password_reset
Revises: 0045_provider_cost_day
Create Date: 2026-11-23 16:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision = '0046_password_reset'
down_revision = '0045_provider_cost_day'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'user',
        sa.Column('session_version', sa.Integer(), server_default='0', nullable=False),
    )
    op.create_table(
        'password_reset_request',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('address_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_password_reset_request_email_hash'), 'password_reset_request', ['email_hash'], unique=False)
    op.create_index(op.f('ix_password_reset_request_address_hash'), 'password_reset_request', ['address_hash'], unique=False)
    op.create_index(op.f('ix_password_reset_request_user_id'), 'password_reset_request', ['user_id'], unique=False)
    op.create_index(op.f('ix_password_reset_request_token_hash'), 'password_reset_request', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_password_reset_request_token_hash'), table_name='password_reset_request')
    op.drop_index(op.f('ix_password_reset_request_user_id'), table_name='password_reset_request')
    op.drop_index(op.f('ix_password_reset_request_address_hash'), table_name='password_reset_request')
    op.drop_index(op.f('ix_password_reset_request_email_hash'), table_name='password_reset_request')
    op.drop_table('password_reset_request')
    op.drop_column('user', 'session_version')
