"""workspaces never bring a model key: Connexity's own keys run every model call

Revision ID: 0035_no_workspace_model_keys
Revises: 0034_onboarding_completed
Create Date: 2026-11-18 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0035_no_workspace_model_keys'
down_revision = '0034_onboarding_completed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('company', 'openai_api_key_encrypted')
    op.drop_column('company', 'openai_api_key_masked')
    op.drop_column('company', 'anthropic_api_key_encrypted')
    op.drop_column('company', 'anthropic_api_key_masked')
    op.drop_column('company', 'preferred_llm_provider')


def downgrade() -> None:
    op.add_column('company', sa.Column('preferred_llm_provider', sa.VARCHAR(), nullable=True))
    op.add_column('company', sa.Column('anthropic_api_key_masked', sa.VARCHAR(length=128), nullable=True))
    op.add_column('company', sa.Column('anthropic_api_key_encrypted', sa.Text(), nullable=True))
    op.add_column('company', sa.Column('openai_api_key_masked', sa.VARCHAR(length=128), nullable=True))
    op.add_column('company', sa.Column('openai_api_key_encrypted', sa.Text(), nullable=True))
