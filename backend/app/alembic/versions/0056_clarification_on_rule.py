"""A clarification is attached to its rule; behaviour no rule covers is a prompt gap

Revision ID: 0056_clarification_on_rule
Revises: 0055_call_agent_words
Create Date: 2026-11-26 21:00:00.000000

Plan: plans/2026-11-26-clarification-on-rule.md. Questions raised before this have no
rule key, so they are prompt gaps, as every one of them asked about behaviour the
prompt did not cover; the rules earlier answers made stay until a spec written from a
prompt that covers them closes the gap.
"""
import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0056_clarification_on_rule'
down_revision = '0055_call_agent_words'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('clarification', sa.Column('rule_key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('clarification', sa.Column('gap_topic', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True))
    op.add_column('clarification', sa.Column('replaces_id', sa.Uuid(), nullable=True))
    op.add_column('clarification', sa.Column('closed_spec_id', sa.Uuid(), nullable=True))
    op.add_column('clarification', sa.Column('closed_rule_key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('clarification', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_clarification_rule_key'), 'clarification', ['rule_key'], unique=False)
    op.create_index(op.f('ix_clarification_replaces_id'), 'clarification', ['replaces_id'], unique=False)
    op.create_index(op.f('ix_clarification_closed_spec_id'), 'clarification', ['closed_spec_id'], unique=False)
    op.create_foreign_key('clarification_replaces_id_fkey', 'clarification', 'clarification', ['replaces_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('clarification_closed_spec_id_fkey', 'clarification', 'spec', ['closed_spec_id'], ['id'], ondelete='SET NULL')
    # Each answer's "rule" is now the sentence it adds.
    op.execute(
        """
        UPDATE clarification SET answers = (
            SELECT jsonb_agg(
                jsonb_build_object('label', a -> 'label', 'sentence', a -> 'rule')
                ORDER BY n
            )
            FROM jsonb_array_elements(answers) WITH ORDINALITY AS t(a, n)
        )
        """
    )
    # Replacing a rule by answer is gone: a rule changes only with the prompt.
    op.drop_column('clarification', 'replaces_key')
    op.add_column('rule_verdict', sa.Column('clarification_ids', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))


def downgrade() -> None:
    op.drop_column('rule_verdict', 'clarification_ids')
    op.add_column('clarification', sa.Column('replaces_key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.execute(
        """
        UPDATE clarification SET answers = (
            SELECT jsonb_agg(
                jsonb_build_object('label', a -> 'label', 'rule', a -> 'sentence')
                ORDER BY n
            )
            FROM jsonb_array_elements(answers) WITH ORDINALITY AS t(a, n)
        )
        """
    )
    op.drop_constraint('clarification_closed_spec_id_fkey', 'clarification', type_='foreignkey')
    op.drop_constraint('clarification_replaces_id_fkey', 'clarification', type_='foreignkey')
    op.drop_index(op.f('ix_clarification_closed_spec_id'), table_name='clarification')
    op.drop_index(op.f('ix_clarification_replaces_id'), table_name='clarification')
    op.drop_index(op.f('ix_clarification_rule_key'), table_name='clarification')
    for column in ('closed_at', 'closed_rule_key', 'closed_spec_id', 'replaces_id', 'gap_topic', 'rule_key'):
        op.drop_column('clarification', column)
