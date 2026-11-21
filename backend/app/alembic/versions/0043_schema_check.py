"""A simulated call keeps what checking its tool arguments against the tools' schemas
found

Revision ID: 0043_schema_check
Revises: 0042_run_progress
Create Date: 2026-11-20 23:30:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0043_schema_check'
down_revision = '0042_run_progress'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'test_case_result',
        sa.Column('schema_check', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('test_case_result', 'schema_check')
