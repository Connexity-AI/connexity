"""drop clarification suggestion: Connexity stores no answers suggested by an assistant

Revision ID: 0023_drop_suggestion
Revises: 0022_clarification_suggestion
Create Date: 2026-11-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0023_drop_suggestion'
down_revision = '0022_clarification_suggestion'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('fk_clarification_suggested_by', 'clarification', type_='foreignkey')
    op.drop_index(op.f('ix_clarification_suggested_by'), table_name='clarification')
    op.drop_column('clarification', 'suggested_at')
    op.drop_column('clarification', 'suggested_assistant')
    op.drop_column('clarification', 'suggested_by')
    op.drop_column('clarification', 'suggestion_confident')
    op.drop_column('clarification', 'suggestion_why')
    op.drop_column('clarification', 'suggested_answer')


def downgrade() -> None:
    # The columns come back empty: dropped suggestions are gone.
    op.add_column('clarification', sa.Column('suggested_answer', sqlmodel.sql.sqltypes.AutoString(length=1), nullable=True))
    op.add_column('clarification', sa.Column('suggestion_why', sa.Text(), nullable=True))
    op.add_column('clarification', sa.Column('suggestion_confident', sa.Boolean(), nullable=True))
    op.add_column('clarification', sa.Column('suggested_by', sa.Uuid(), nullable=True))
    op.add_column('clarification', sa.Column('suggested_assistant', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
    op.add_column('clarification', sa.Column('suggested_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_clarification_suggested_by'), 'clarification', ['suggested_by'], unique=False)
    op.create_foreign_key('fk_clarification_suggested_by', 'clarification', 'user', ['suggested_by'], ['id'], ondelete='SET NULL')
