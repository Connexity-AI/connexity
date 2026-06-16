"""company llm credentials

Revision ID: mt_llm_creds_001
Revises: z6a7b8c9d0e1
Create Date: 2026-06-06

Adds per-tenant LLM credential columns to the ``company`` table. Each
company stores its own encrypted OpenAI / Anthropic API keys + a masked
preview, plus a preferred provider for features that don't pin one.
"""

import sqlalchemy as sa
from alembic import op

revision = "mt_llm_creds_001"
down_revision = "z6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres enum for the preferred provider.
    op.execute("CREATE TYPE llmprovider AS ENUM ('openai', 'anthropic')")

    op.add_column(
        "company",
        sa.Column("openai_api_key_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "company",
        sa.Column("openai_api_key_masked", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "company",
        sa.Column("anthropic_api_key_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "company",
        sa.Column("anthropic_api_key_masked", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "company",
        sa.Column(
            "preferred_llm_provider",
            sa.Enum("openai", "anthropic", name="llmprovider", native_enum=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("company", "preferred_llm_provider")
    op.drop_column("company", "anthropic_api_key_masked")
    op.drop_column("company", "anthropic_api_key_encrypted")
    op.drop_column("company", "openai_api_key_masked")
    op.drop_column("company", "openai_api_key_encrypted")
    op.execute("DROP TYPE IF EXISTS llmprovider")
