"""call: when its executions were last looked for

Revision ID: 0007_executions_checked_at
Revises: 0006_component_versions
Create Date: 2026-10-09
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0007_executions_checked_at'
down_revision = '0006_component_versions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('call', sa.Column('executions_checked_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('call', 'executions_checked_at')
