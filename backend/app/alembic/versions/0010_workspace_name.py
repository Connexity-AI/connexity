"""a company is a workspace and has a name

Revision ID: 0010_workspace_name
Revises: 0009_check_runs_and_issues
Create Date: 2026-11-12 15:35:18.595136

Existing companies are named after the email domain of one of their users (users
have no creation time, so the lowest id is taken, which is repeatable), or
"Workspace" when they have none.
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0010_workspace_name'
down_revision = '0009_check_runs_and_issues'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'company',
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    )
    op.execute(
        """
        UPDATE company
        SET name = COALESCE(
            (
                SELECT NULLIF(LEFT(LOWER(SPLIT_PART(u.email, '@', 2)), 255), '')
                FROM "user" u
                WHERE u.company_id = company.id
                ORDER BY u.id
                LIMIT 1
            ),
            'Workspace'
        )
        """
    )
    op.alter_column('company', 'name', nullable=False)


def downgrade() -> None:
    op.drop_column('company', 'name')
