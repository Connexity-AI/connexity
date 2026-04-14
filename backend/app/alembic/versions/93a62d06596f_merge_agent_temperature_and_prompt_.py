"""merge agent_temperature and prompt_editor_session_state heads

Revision ID: 93a62d06596f
Revises: f2a3b4c5d6e7, f8e9d0c1b2a3
Create Date: 2026-04-14 17:21:01.277297

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '93a62d06596f'
down_revision = ('f2a3b4c5d6e7', 'f8e9d0c1b2a3')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
