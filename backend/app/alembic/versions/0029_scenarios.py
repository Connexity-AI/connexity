"""scenarios: the caller's goal and behaviour, the agent's variables, and the spec
rules a scenario lists

Revision ID: 0029_scenarios
Revises: 0028_spec_rule_critical
Create Date: 2026-11-17 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0029_scenarios'
down_revision = '0028_spec_rule_critical'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('test_case', sa.Column('caller_goal', sa.Text(), nullable=True))
    op.add_column('test_case', sa.Column('caller_behaviour', sa.Text(), nullable=True))
    op.add_column(
        'test_case',
        sa.Column('agent_variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_table(
        'scenario_rule',
        sa.Column('test_case_id', sa.Uuid(), nullable=False),
        sa.Column('rule_key', sa.String(length=64), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('agent_id', sa.Uuid(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['company.id']),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_case.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('test_case_id', 'rule_key'),
    )
    op.create_index(op.f('ix_scenario_rule_agent_id'), 'scenario_rule', ['agent_id'], unique=False)
    op.create_index(op.f('ix_scenario_rule_company_id'), 'scenario_rule', ['company_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_scenario_rule_company_id'), table_name='scenario_rule')
    op.drop_index(op.f('ix_scenario_rule_agent_id'), table_name='scenario_rule')
    op.drop_table('scenario_rule')
    op.drop_column('test_case', 'agent_variables')
    op.drop_column('test_case', 'caller_behaviour')
    op.drop_column('test_case', 'caller_goal')
