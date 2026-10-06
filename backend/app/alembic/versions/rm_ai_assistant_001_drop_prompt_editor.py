"""drop in-app AI assistant: prompt editor tables and agent.editor_guidelines

Revision ID: rm_ai_assistant_001
Revises: mt_llm_creds_001
Create Date: 2026-09-23

The in-app AI assistant (prompt editor chat + agent guidelines) was removed in
favour of external assistants (Claude Code, Cursor, Codex) driving Connexity
via MCP / CLI. Downgrade restores the schema but not the data.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "rm_ai_assistant_001"
down_revision = "mt_llm_creds_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("prompt_editor_message")
    op.drop_table("prompt_editor_session")
    op.drop_column("agent", "editor_guidelines")


def downgrade() -> None:
    op.add_column(
        "agent",
        sa.Column("editor_guidelines", sa.Text(), nullable=True),
    )

    op.create_table(
        "prompt_editor_session",
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("base_prompt", sa.Text(), nullable=True),
        sa.Column("edited_prompt", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agent.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"]),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_prompt_editor_session_company_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prompt_editor_session_agent_id", "prompt_editor_session", ["agent_id"]
    )
    op.create_index(
        "ix_prompt_editor_session_created_by", "prompt_editor_session", ["created_by"]
    )
    op.create_index(
        "ix_prompt_editor_session_company_id", "prompt_editor_session", ["company_id"]
    )

    op.create_table(
        "prompt_editor_message",
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("tool_calls", JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["prompt_editor_session.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_prompt_editor_message_company_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prompt_editor_message_session_id", "prompt_editor_message", ["session_id"]
    )
    op.create_index(
        "ix_prompt_editor_message_company_id", "prompt_editor_message", ["company_id"]
    )
