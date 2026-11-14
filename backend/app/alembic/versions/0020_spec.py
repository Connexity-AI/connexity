"""spec: each agent's spec, version by version, and its rules

Revision ID: 0020_spec
Revises: 0019_issue_archive
Create Date: 2026-11-14 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0020_spec'
down_revision = '0019_issue_archive'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'spec',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('agent_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('agent_version', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('prompt_fingerprint', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column('origin', sa.Enum('written', 'adopted', name='specorigin', native_enum=False, length=32), nullable=False),
        sa.Column('previous_id', sa.Uuid(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('created_by_email', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column('assistant_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['company.id']),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['previous_id'], ['spec.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id', 'version', name='uq_spec_agent_version'),
    )
    op.create_index(op.f('ix_spec_agent_id'), 'spec', ['agent_id'], unique=False)
    op.create_index(op.f('ix_spec_company_id'), 'spec', ['company_id'], unique=False)
    op.create_index(op.f('ix_spec_created_by'), 'spec', ['created_by'], unique=False)
    op.create_index(op.f('ix_spec_previous_id'), 'spec', ['previous_id'], unique=False)
    op.create_table(
        'spec_rule',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('spec_id', sa.Uuid(), nullable=False),
        sa.Column('key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Uuid(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('source', sa.Enum('prompt', 'clarification', name='specrulesource', native_enum=False, length=32), nullable=False),
        sa.Column('quote', sa.Text(), nullable=True),
        sa.Column('clarification_id', sa.Uuid(), nullable=True),
        sa.Column('touches', sa.Enum('money', 'safety', 'compliance', name='specruletouches', native_enum=False, length=32), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['category.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['company_id'], ['company.id']),
        sa.ForeignKeyConstraint(['spec_id'], ['spec.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('spec_id', 'key', name='uq_spec_rule_key'),
    )
    op.create_index(op.f('ix_spec_rule_category_id'), 'spec_rule', ['category_id'], unique=False)
    op.create_index(op.f('ix_spec_rule_company_id'), 'spec_rule', ['company_id'], unique=False)
    op.create_index(op.f('ix_spec_rule_spec_id'), 'spec_rule', ['spec_id'], unique=False)


def downgrade():
    op.drop_table('spec_rule')
    op.drop_table('spec')
