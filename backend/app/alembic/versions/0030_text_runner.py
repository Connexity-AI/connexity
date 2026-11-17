"""text runner: runs of scenarios, rule verdicts, and code-check findings on simulated
calls

Revision ID: 0030_text_runner
Revises: 0029_scenarios
Create Date: 2026-11-17 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0030_text_runner'
down_revision = '0029_scenarios'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('run', 'eval_config_id', existing_type=sa.Uuid(), nullable=True)
    op.add_column('run', sa.Column('scope', sa.String(length=32), nullable=True))
    op.add_column('run', sa.Column('set_name', sa.String(length=255), nullable=True))
    op.add_column('run', sa.Column('repeats', sa.Integer(), nullable=True))
    op.add_column('run', sa.Column('spec_id', sa.Uuid(), nullable=True))
    op.add_column('run', sa.Column('platform_version', sa.String(length=64), nullable=True))
    op.add_column('run', sa.Column('status_detail', sa.String(length=1024), nullable=True))
    op.create_foreign_key(
        'run_spec_id_fkey', 'run', 'spec', ['spec_id'], ['id'], ondelete='SET NULL'
    )
    op.add_column(
        'test_case_result',
        sa.Column('check_findings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        'test_case_result',
        sa.Column('default_fakes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_table(
        'rule_verdict',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('agent_id', sa.Uuid(), nullable=False),
        sa.Column('run_id', sa.Uuid(), nullable=False),
        sa.Column('test_case_result_id', sa.Uuid(), nullable=False),
        sa.Column('test_case_id', sa.Uuid(), nullable=False),
        sa.Column('rule_key', sa.String(length=64), nullable=False),
        sa.Column('outcome', sa.String(length=32), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('turns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('critical', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['company.id']),
        sa.ForeignKeyConstraint(['run_id'], ['run.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_case.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['test_case_result_id'], ['test_case_result.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('test_case_result_id', 'rule_key'),
    )
    op.create_index(op.f('ix_rule_verdict_agent_id'), 'rule_verdict', ['agent_id'], unique=False)
    op.create_index(op.f('ix_rule_verdict_company_id'), 'rule_verdict', ['company_id'], unique=False)
    op.create_index(op.f('ix_rule_verdict_run_id'), 'rule_verdict', ['run_id'], unique=False)
    op.create_index(op.f('ix_rule_verdict_rule_key'), 'rule_verdict', ['rule_key'], unique=False)
    op.create_index(
        op.f('ix_rule_verdict_test_case_id'), 'rule_verdict', ['test_case_id'], unique=False
    )


def downgrade() -> None:
    op.drop_table('rule_verdict')
    op.drop_column('test_case_result', 'default_fakes')
    op.drop_column('test_case_result', 'check_findings')
    op.drop_constraint('run_spec_id_fkey', 'run', type_='foreignkey')
    for column in ('status_detail', 'platform_version', 'spec_id', 'repeats', 'set_name', 'scope'):
        op.drop_column('run', column)
    # Runs of scenarios without a set cannot survive the column becoming required.
    op.execute("DELETE FROM run WHERE eval_config_id IS NULL")
    op.alter_column('run', 'eval_config_id', existing_type=sa.Uuid(), nullable=False)
