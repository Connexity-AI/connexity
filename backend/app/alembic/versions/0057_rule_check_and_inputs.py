"""Each spec rule's check type and the call inputs it needs

Revision ID: 0057_rule_check_and_inputs
Revises: 0056_clarification_on_rule
Create Date: 2026-11-26 23:00:00.000000

Plan: plans/2026-11-26-rule-data-and-check.md. Every existing rule becomes a classifier
check on the call alone (Decided, Dmytro 2026-11-26: "Classifier by default").
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0057_rule_check_and_inputs'
down_revision = '0056_clarification_on_rule'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('spec_rule', sa.Column('check', sa.Enum('classifier', 'classifier_then_llm', 'llm', name='specchecktype', native_enum=False, length=32), server_default='classifier', nullable=False))
    op.add_column('spec_rule', sa.Column('inputs', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))


def downgrade() -> None:
    op.drop_column('spec_rule', 'inputs')
    op.drop_column('spec_rule', 'check')
