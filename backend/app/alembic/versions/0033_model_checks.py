"""model checks: stored model answers, and the "rule" check kind renamed "code_based"

Revision ID: 0033_model_checks
Revises: 0032_issue_fix_live_at
Create Date: 2026-11-17 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0033_model_checks'
down_revision = '0032_issue_fix_live_at'
branch_labels = None
depends_on = None


def _rename_kind(old: str, new: str) -> None:
    op.execute(f"UPDATE finding SET kind = '{new}' WHERE kind = '{old}'")
    # A simulated call keeps its code-check findings as JSON.
    op.execute(
        f"""
        UPDATE test_case_result
        SET check_findings = (
            SELECT jsonb_agg(
                CASE WHEN e->>'kind' = '{old}'
                     THEN jsonb_set(e, '{{kind}}', '"{new}"')
                     ELSE e END
            )
            FROM jsonb_array_elements(check_findings) AS e
        )
        WHERE check_findings @> '[{{"kind": "{old}"}}]'
        """
    )


def upgrade() -> None:
    op.create_table(
        'model_answer',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('call_id', sa.Uuid(), nullable=False),
        sa.Column('check_type', sa.String(length=64), nullable=False),
        sa.Column('check_version', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('ok', 'failed', name='modelanswerstatus', native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column('model', sa.String(length=128), nullable=False),
        sa.Column('answer', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('requests', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['call_id'], ['call.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['company.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'call_id', 'check_type', 'check_version', name='uq_model_answer_call_check'
        ),
    )
    op.create_index('ix_model_answer_call_id', 'model_answer', ['call_id'])
    op.create_index('ix_model_answer_company_id', 'model_answer', ['company_id'])
    op.create_index('ix_model_answer_created_at', 'model_answer', ['created_at'])
    _rename_kind('rule', 'code_based')


def downgrade() -> None:
    _rename_kind('code_based', 'rule')
    op.drop_index('ix_model_answer_created_at', table_name='model_answer')
    op.drop_index('ix_model_answer_company_id', table_name='model_answer')
    op.drop_index('ix_model_answer_call_id', table_name='model_answer')
    op.drop_table('model_answer')
