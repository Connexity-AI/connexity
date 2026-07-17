"""add requirement table

Revision ID: 8a58cbd53c5e
Revises: mt_llm_creds_001
Create Date: 2026-06-16

Immutable, LLM-extracted requirements snapshotted per agent version. Each row is
an atomic, testable statement of what the agent must do; test-case generation
reads these instead of the raw system prompt so single-prompt and Retell
conversation-flow agents share one source of truth.
"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "8a58cbd53c5e"
down_revision = "mt_llm_creds_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requirement",
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "category", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column(
            "source_ref", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("agent_version_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agent.id"]),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agent_version.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_requirement_agent_id"), "requirement", ["agent_id"], unique=False
    )
    op.create_index(
        "ix_requirement_agent_version_id",
        "requirement",
        ["agent_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_requirement_company_id"), "requirement", ["company_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_requirement_company_id"), table_name="requirement")
    op.drop_index("ix_requirement_agent_version_id", table_name="requirement")
    op.drop_index(op.f("ix_requirement_agent_id"), table_name="requirement")
    op.drop_table("requirement")
